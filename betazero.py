import chess
import random
import numpy as np
import torch
import torch.nn as nn
import util
import time
from torchsummary import summary
from copy import deepcopy
import sys
import os


# simple value mlp
class SimpleValueNetwork(nn.Module):
    def __init__(self):
        super(SimpleValueNetwork, self).__init__()

        self.fc = nn.Sequential( 
            nn.Linear(13*8*8 + 1, 4096),
            nn.ReLU(),
            nn.Linear(4096, 4096),
            nn.ReLU(),
            nn.Linear(4096, 2048),
            nn.ReLU(),
            nn.Linear(2048, 2048),
            nn.ReLU(),
            nn.Linear(2048, 2048),
            nn.ReLU(),
            nn.Linear(2048, 1024),
            nn.ReLU(),
            nn.Linear(1024, 1),
        )

    def forward(self, x):
        x = self.fc(x)

        return x



# resnet block
class ResBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ResBlock, self).__init__()

        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.leaky1 = nn.LeakyReLU()
        self.leaky2 = nn.LeakyReLU()

    def forward(self, x):
        residual = x
        out = self.conv1(x)
        #out = self.bn1(out)
        out = self.leaky1(out)
        out = self.conv2(out)
        #out = self.bn2(out)
        out += residual
        out = self.leaky2(out)
        return out

# value network
class ValueNetwork(nn.Module):
    def __init__(self):
        super(ValueNetwork, self).__init__()

        self.conv1 = nn.Conv2d(13, 254, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(254)
        self.res1 = ResBlock(254, 254)
        self.res2 = ResBlock(254, 254)
        self.res3 = ResBlock(254, 254)
        self.res4 = ResBlock(254, 254)
        self.res5 = ResBlock(254, 254)
        self.res6 = ResBlock(254, 254)
        self.res7 = ResBlock(254, 254)

        self.conv2 = nn.Conv2d(254, 32, kernel_size=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.fc1 = nn.Linear(64*32, 64*32)
        self.fc2 = nn.Linear(64*32, 64*32)
        self.fc3 = nn.Linear(64*32, 64*32)
        self.fc4 = nn.Linear(64*32, 1)

        self.leaky1 = nn.LeakyReLU()
        self.leaky2 = nn.LeakyReLU()
        self.leaky3 = nn.LeakyReLU()
        self.leaky4 = nn.LeakyReLU()
        self.leaky5 = nn.LeakyReLU()
    
    def forward(self, x):
        x = self.conv1(x)
        #x = self.bn1(x)
        x = self.leaky1(x)
        x = self.res1(x)
        x = self.res2(x)
        x = self.res3(x)
        x = self.res4(x)
        x = self.res5(x)
        x = self.res6(x)
        x = self.res7(x)

        x = self.conv2(x)
        #x = self.bn2(x)
        x = self.leaky2(x)
        x = x.view(-1, 64*32)
        x = self.fc1(x)
        x = self.leaky3(x)
        x = self.fc2(x)
        x = self.leaky4(x)
        x = self.fc3(x)
        x = self.leaky5(x)
        x = self.fc4(x)

        return x



class Node:
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0

    def add_child(self, child):
        self.children.append(child)

    def is_leaf(self):
        return len(self.children) == 0

    def is_root(self):
        return self.parent is None

    def fully_expanded(self):
        return len(self.children) == len(list(self.state.legal_moves))

    def __str__(self):
        return str(self.state)

EXPLORATION_CONSTANT = 0.02

total_visits = 0

DEVICE = "cuda"

# TODO
# train nn and generate data in parallel

total_positions = []

# upper confidence bound
def ucb(node):
    return node.value / node.visits + EXPLORATION_CONSTANT * np.sqrt(total_visits / node.visits + 1)

# update root
def update_root(root, move):
   for child in root.children:
       if str(child.state.peek()) == str(move):
           root = child
           root.parent = None
           print("updated")
           break

def get_legal_move_values(network, board, moves, legal_moves):
    values = []
    new_board = chess.Board(board.fen())
    for move in legal_moves:
        new_board.push(move)
        state = util.one_hot_board(util.board_to_list(new_board)).unsqueeze(0)
        state *= (1.0 if new_board.turn == True else -1.0)
        #state = torch.flatten(state) * (1.0 if new_board.turn == True else -1.0)
        #state = torch.cat((state, torch.tensor([1.0 / (moves+1)], dtype=torch.float32)))
        state = state.to(DEVICE)
        value = network(state)
        values.append(value.item())
        # unmove board
        new_board.pop()
    
    #softmax
    values = np.array(values)
    values = np.exp(values) / np.sum(np.exp(values))

    # sample from distribution and get index
    index = random.choices(list(range(len(values))), weights=values)[0]

    return legal_moves[index], values[index]



throwboard = chess.Board()

def mcts(root, board, network, num_simulations, move_num):
    boardturn = board.turn
    global total_visits
    
    for _ in range(num_simulations):
        #print("simulating", _ / num_simulations * 100, end="\r)
        cur_depth = 1
        #print(f"{_}, {(_ / num_simulations * 100):.2f}%", end="\r")
        
        node = root


        if node.parent == None:
            if not node.fully_expanded():
                #print("root expand")
                #print(node.state.legal_moves)
                unexpanded_moves = list(set(node.state.legal_moves) - set([child.state.peek() for child in node.children]))
                move = random.choice(unexpanded_moves)
                
                # move, v = get_legal_move_values(network, node.state, move_num, list(node.state.legal_moves))
                
                #new_state = node.state.copy()
                new_state = chess.Board(node.state.fen())
                #new_state.set_board_fen(node.state.board_fen())
                new_state.push(move)
                new_node = Node(new_state, node)
                node.add_child(new_node)
                node = new_node
                cur_depth += 1 

        while node.visits > 0:
            # select
            if node.fully_expanded():
                # handle no children
                if len(node.children) == 0:
                    # print("select: no children")
                    break

                #print("select")

                # print all ucb values
                # for child in node.children:
                #    print(f'({ucb(child):.2f} {child.value:.2f} {child.visits})', end=", ")
                # print("\n\n\n")

                node = max(node.children, key=ucb)

                #print("node select")
                cur_depth += 1
            # expand
            else: 
                #print("node expand")
                unexpanded_moves = list(set(node.state.legal_moves) - set([child.state.peek() for child in node.children]))
                move = random.choice(unexpanded_moves)

                #move, v = get_legal_move_values(network, node.state, move_num, list(node.state.legal_moves))

                #new_state = node.state.copy()
                new_state = chess.Board(node.state.fen())
                #new_state.set_board_fen(node.state.board_fen())
                new_state.push(move)
                new_node = Node(new_state, node)
                node.add_child(new_node)
                node = new_node
                cur_depth += 1

        # simulate value with rollout
        # total_value = 0
        nodeturn = node.state.turn
        # value = -.25
        # while value == -.25:
            
        #     throwboard.set_board_fen(node.state.board_fen())
        #     while not throwboard.is_game_over():
        #         move = random.choice(list(throwboard.legal_moves))
        #         throwboard.push(move)
        #     result = throwboard.outcome()
        #     #print(result.winner, boardturn, nodeturn)
        #     value = 1 if result.winner == nodeturn else -1 if result.winner != nodeturn else -.25

        #     #value = 1 if result.winner == node.state.turn else -1 if result.winner != node.state.turn else 0
        #     rollout_value = value
        # node.value = total_value


        # get value from nn
        state = util.one_hot_board(util.board_to_list(node.state)).unsqueeze(0)
        #print(state.shape)
        #state = torch.flatten(state) * (1.0 if node.state.turn == True else -1.0)
        state *= (1.0 if node.state.turn == True else -1.0)

        #state = torch.cat((state, torch.tensor([1.0 / move_num], dtype=torch.float32)))

        state = state.to(DEVICE)
        #state = torch.cat((torch.flatten(state), torch.tensor([node.state.turn], dtype=torch.float32)))
        #print(state)
        value = network(state)
        #print(value.item())
        total_value = -(value.item())
        # total_value = -rollout_value
        node.value = total_value

        node.visits += 1
        total_visits += 1

        # backpropagate
        while not node.is_root():
            node = node.parent

            # flip value if not current player
            v = total_value
            if node.state.turn != nodeturn:
                v = -total_value

            node.value += v
            node.visits += 1
            total_visits += 1
    #return max(root.children, key=lambda node: node.visits).state.peek()

    # return sample from the distribution of visits
    visits = [child.visits for child in root.children]
    values = [child.value / child.visits for child in root.children]
    # print(len(visits), visits)
    
    if len(visits) == 0:
        print(board)
        print(board.outcome().winner, board.is_game_over(), board.result())
        return root.state.peek(), root

    # print values

    
    print(visits)
    # print(values)
    # sample visits
    bruv = random.choices(root.children, weights=visits)
    nextnoder = bruv[0]

    # print(bruv)

    nextnoder.parent = None
    return nextnoder.state.peek(), nextnoder



def self_play(network, crownnet):
    global total_visits
    global total_positions
    start_time = time.time()
    moves = 1

    optimizer = torch.optim.Adam(network.parameters(), 0.0001)
    criterion = nn.MSELoss().to(DEVICE)

    for game in range(1000000):
        
        # if game % 1 == 0:
        #     # save model
        print("\n\n\nSAVING", game, "\n\n\n")
        torch.save(network.state_dict(), "./betazero.pth")


        states = []
        values = []
        

        while len(states) < 50:
            total_visits = 0
            game_size = 0
            breads = []
            board = chess.Board()
            root = Node(board)
            moves = 1
            too_long = False
            while not board.is_game_over():
                game_size += 1
                
                # if game_size > 65:
                #     too_long = True
                #     break

                move, root = mcts(root, board, network, 75, moves)
                board.push(move)
                state = util.one_hot_board(util.board_to_list(board))
                
                state *= (1.0 if board.turn == True else -1.0)
                
                #state = torch.flatten(state) * (1.0 if board.turn == True else -1.0)
                #state = torch.cat((state, torch.tensor([1.0 / moves], dtype=torch.float32)))

                #print(state.shape)
                #state = torch.cat((torch.flatten(state), torch.tensor([board.turn], dtype=torch.float32)))
                breads.append(board.turn)
                # print(state, type(state))
                states.append(state)
                
                moves += 1
                # show the visual board
                # print(board)
                # print()
                # time.sleep(2)
                print(moves, end="\r")
            #print(states)
            #

            # if board.outcome().winner == None:
            #     #continue # just skip training games that exceed move limit
            #     values = torch.ones((statestensor.shape[0]))
                
            #     for i in range(values.shape[0]):
            #         values[i] = 1 if i % 2 == 0 else -1
                
                #values = values * -.05

            if not too_long and (board.outcome().winner != None or random.random() < 0.15): #0.025
                
                #values = torch.ones((statestensor.shape[0]))
                for i in range(game_size):
                    if board.outcome().winner == None:
                        values.append(torch.tensor(-0.25))
                    else:
                        values.append(torch.tensor(1.0) if board.outcome().winner == breads[i] else torch.tensor(-1.0) if board.outcome().winner != breads[i] else torch.tensor(.5))
                    total_positions.append([states[i], values[i]])
                print('wowee', len(states), len(values), board.outcome().winner)
            else:
                states = states[:-game_size]
                continue


        # discount values
        # for i in range(values.shape[0]):
        #     if i < 50:
        #         values[i] *= 0.985 ** (50 - i)
        #     else:
        #         break

        if len(values) != len(states):
            continue
        
        # sample 2048 positions from total_positions
        #print(len(total_positions))

        if len(total_positions) > 10000:
            # remove old
            total_positions = total_positions[-10000:]


        # sample = random.sample(total_positions, 2048 if len(total_positions) > 2048 else len(total_positions))
        # statestensor = [x[0] for x in sample]
        # valuestensor = [x[1] for x in sample]

        # statestensor = torch.stack(statestensor).to(DEVICE)
        # valuestensor = torch.stack(valuestensor).to(DEVICE)

        # statestensor = torch.stack(states).to(DEVICE)
        # values = torch.tensor(values, dtype=torch.float32).to(DEVICE)

        # initial loss is inf
        loss = 10000
        #prevnet = 
        
        threshold = 0.1 if len(total_positions) >= 2048 else 0.4
        print("num total positions: \n", len(total_positions), "\n\n")
        while loss > threshold:
            sample = random.sample(total_positions, 2048 if len(total_positions) > 2048 else len(total_positions))
            
            #print(sample)

            statestensor = [x[0] for x in sample]
            valuestensor = [x[1] for x in sample]

            

            statestensor = torch.stack(statestensor).to(DEVICE)
            valuestensor = torch.stack(valuestensor).to(DEVICE)
            print(statestensor.shape)
            #print("training")    
            optimizer.zero_grad()
            output = network(statestensor)
            loss = criterion(output.squeeze(), valuestensor)
            loss.backward()
            optimizer.step()
            print("OUTPUT SHAPE: ", output.shape, "\nOUTPUT: ", output, "\nVALUES: ", valuestensor, "\nLOSS: ", loss.item())
        
        # pit the new network against the previous network
        # wins = 0
        # losses = 0
        # draws = 0
        # for _ in range(10):
        #     bird = chess.Board()
        #     rut = Node(bird)
        #     moves = 1
        #     print("pitting game", _ + 1, end="\r")
        #     while not bird.is_game_over():
        #         #rut = Node(bird)
        #         legal_moves = list(bird.legal_moves)
        #         move, v = get_legal_move_values(crownnet, bird, moves, legal_moves)


        #         bird.push(move)
        #         moves += 1
        #         if bird.is_game_over():
        #             break
        #         legal_moves = list(bird.legal_moves)
        #         move, v = get_legal_move_values(network, bird, moves, legal_moves)


        #         bird.push(move)
        #         moves += 1
                
        #     result = bird.outcome().winner
        #     if result == True:
        #         wins += 1
        #     elif result == False:
        #         losses += 1
        #     else:
        #         draws += 1
        
        # if wins > losses:
        #     network = deepcopy(crownnet)
        #     print("got better! or too many draws :(", wins, losses, draws)
        # else:
        #     crownnet = deepcopy(network)
        #     print("no improvement", wins, losses, draws)

    end_time = time.time()
    print()
    print("game done ", end_time - start_time)
    print(board.result())
    print(board.outcome().winner)


if __name__ == "__main__":

    nnet = ValueNetwork().to("cuda")
    prevnet = ValueNetwork()
    
    
    print(summary(nnet, (13, 8, 8)))
    nnet.load_state_dict(torch.load("./betazero.pth"))
    # prevnet.load_state_dict(torch.load("./betazero.pth"))


    # bord = chess.Board()
    # state = util.one_hot_board(util.board_to_list(bord)).unsqueeze(0)
    # print(state)


    # human vs ai
    # board = chess.Board()
    # root = Node(board)
    # while not board.is_game_over():
        
    #     print(board)
    #     move = input("move: ")
    #     board.push_uci(move)
    #     root = Node(board)
    #     move, root = mcts(root, board, nnet, 400, 1)
    #     board.push(move)



    #print(mcts(chess.Board()))
    self_play(nnet, prevnet)