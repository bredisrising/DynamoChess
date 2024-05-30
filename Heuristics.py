import chess
from CentControlHeuristic import CenterControlClass


piece_material = {
    'P': 1,
    'N': 3,
    'B': 3,
    'R': 5,
    'Q': 9,
    'K': 50
}

table_base = {
    'p': [
        [0, 0, 0, 0, 0, 0, 0, 0], 
        [1, 1, 1, 1, 1, 1, 1, 1], 
        [1, 1, 1, 1, 1, 0, 1, 1], 
        [3, 3, 4, 5, 5, 0, 3, 3], 
        [5, 5, 6, 6, 6, 2, 5, 5], 
        [7, 7, 8, 8, 8, 4, 7, 7], 
        [8, 8, 9, 9, 9, 8, 8, 8], 
        [10, 10, 10, 10, 10, 10, 10, 10]
    ], 
    'n': [
        [0, 8, 0, 0, 0, 0, 8, 0], 
        [1, 1, 1, 1, 1, 1, 1, 1], 
        [4, 3, 5, 3, 3, 5, 3, 4], 
        [5, 4, 6, 6, 6, 6, 4, 5], 
        [2, 8, 10, 10, 10, 10, 8, 2], 
        [1, 3, 4, 5, 5, 4, 3, 1], 
        [1, 2, 10, 4, 4, 10, 2, 1], 
        [0, 0, 0, 0, 0, 0, 0, 0]
    ], 
    'b': [
        [2, 0, 1, 0, 0, 1, 0, 2],
        [0, 7, 0, 0, 0, 0, 7, 0],
        [5, 2, 5, 0, 0, 5, 2, 5],
        [1, 3, 10, 0, 0, 10, 3, 1],
        [1, 10, 0, 0, 0, 0, 10, 1],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0]
    ], 
    'k': [
        [8, 10, -10, 0, 0, -10, 10, 8],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [0, 0, -1, -1, -1, -1, 0, 0],
        [-2, -2, -4, -4, -4, -4, -2, -2],
        [-4, -4, -6, -6, -6, -6, -4, -4],
        [-6, -6, -8, -8, -8, -8, -6, -6],
        [-9, -9, -10, -10, -10, -10, -9, -9],
        [-10, -10, -15, -15, -15, -15, -10, -10],
    ],
    'q': [
        [0, 1, 2, 5, 5, 2, 1, 0],
        [3, 3, 4, 5, 5, 4, 3, 3],
        [2, 7, 6, 3, 3, 6, 7, 2],
        [5, 6, 4, 2, 2, 4, 6, 5],
        [6, 7, 7, 2, 2, 7, 7, 6],
        [8, 8, 9, 4, 4, 9, 8, 8],
        [9, 9, 9, 9, 9, 9, 9, 9],
        [6, 7, 7, 7, 7, 7, 7, 7],

    ], 
    'r': [
        [2, 0, 5, 5, 5, 5, 0, 2],
        [4, 0, 5, 5, 5, 5, 0, 4],
        [6, 0, 3, 3, 3, 3, 0, 6],
        [8, 0, 2, 2, 2, 2, 0, 8],
        [6, 0, 3, 3, 3, 3, 0, 6],
        [6, 5, 5, 5, 5, 5, 5, 6],
        [8, 8, 8, 8, 8, 8, 8, 8],
        [10, 9, 8, 10, 10, 8, 9, 10]
    ]
}

table_base_white = {
    'P': list(reversed(table_base['p'])),
    'N': list(reversed(table_base['n'])),
    'B': list(reversed(table_base['b'])),
    'R': list(reversed(table_base['r'])),
    'Q': list(reversed(table_base['q'])),
    'K': list(reversed(table_base['k'])),


}



letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
numbers = ['1', '2', '3', '4', '5', '6', '7', '8']

class Heuristics:
    def __init__(self):
        pass

    def legal_move_manipulation(self, board: chess.Board, uci_translator):
        coordinate_legal_moves = []
        capture_legal_moves = []
        uci_legal_moves = []
        move_object_moves = []
        for move in board.legal_moves:
            move_object_moves.append(move)
            uci_legal_moves.append((str(move)[:2], str(move)[2:]))
            coord_move = uci_translator(str(move))
            coordinate_legal_moves.append(coord_move) # these are flipped
            end_square = coord_move[1]
            if board.piece_at(chess.parse_square(str(move)[2:4])):
                capture_legal_moves.append(move)

            
        return coordinate_legal_moves, capture_legal_moves, uci_legal_moves, move_object_moves

    def piece_values(self, board: chess.Board, curTurn):
        material = 0
        for letter in letters:
            for number in numbers:
                square = letter + number
                piece = str(board.piece_at(chess.parse_square(square)))
                if piece.lower() != 'k' and piece != 'None':
                    if piece.isupper():
                        material += piece_material[piece]
                    else:
                        material -= piece_material[piece.upper()]
                if piece != 'None':
                    if curTurn == chess.BLACK:
                        material += -table_base[piece.lower()][7 - numbers.index(number)][letters.index(letter)] / 100
                    else:
                        material += table_base_white[piece.upper()][numbers.index(number)][letters.index(letter)] / 100
                    
        return material
    
    def get_center_control_value(self, board: chess. Board, center_control, move_object_moves):
        return center_control.centerControl(board, move_object_moves)
    
    def move_ordering(self, moves, board: chess.Board, curTurn):
        moves_scores_list = []
        for move in moves:
            move_score = 0
            uci_move = str(move)
            to_square_indices = (numbers.index(uci_move[3:4]), letters.index(uci_move[2:3]))
            from_square = str(board.piece_at(chess.parse_square(uci_move[:2]))).upper()
            to_square = str(board.piece_at(chess.parse_square(uci_move[2:4]))).upper()
            if to_square != 'NONE':
                move_score += piece_material[to_square] - piece_material[from_square]

            if curTurn == chess.BLACK:
                #print(from_square.lower(), to_square_indices[0], to_square_indices[1])
                #print(table_base[from_square.lower()][to_square_indices[0]][to_square_indices[1]])
                move_score += table_base[from_square.lower()][7 - to_square_indices[0]][to_square_indices[1]]
            else:
                move_score += table_base_white[from_square][to_square_indices[0]][to_square_indices[1]]


            moves_scores_list.append((move, move_score))
        return moves_scores_list, len(moves_scores_list)
    
    def combined_eval(self, board: chess.Board, move_object_moves):
        material = 0
        center_control = 0
        for letter in letters:
            for number in numbers:
                square = letter + number
                piece = str(board.piece_at(chess.parse_square(square)))
                if piece.lower() != 'k' and piece != 'None':
                    if piece.isupper():
                        material += piece_material[piece]
                    else:
                        material -= piece_material[piece.upper()]
                moves = []
                for center_move in center_moves:
                    try:
                        moves.append(chess.Move.from_uci(square + center_move))
                    except:
                        pass
                    #moves = [chess.Move.from_uci(square + center_move) for center_move in center_moves
                #print(moves)
                for move in moves:
                    #try:
                        is_pawn = str(board.piece_at(chess.parse_square(str(move)[2:]))).capitalize() == "P"
                        if is_pawn:
                            if (square[0] == "d" or square[0] == "e") and move in move_object_moves:
                                #print("SQUARE" + str(square[0]))
                                center_control += 2
                            elif (square[0] in one_squares) and move in move_object_moves:
                                center_control += 1
                        else:
                            if move in move_object_moves:
                                #if center_position not in controlled:
                                center_control += 1
                                #controlled.append(center_position) # do we need this TODO
                        # if move in move_object_moves:
                        #     center_control += 1
                    #except:
                    #    pass
        #print("NUMBER " + str(center_control))         
        return (material, center_control)
    