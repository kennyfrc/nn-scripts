import chess
import chess.pgn
import chess.engine
import chess.polyglot
import random
import pdb

# define engines
ENGINE_1="lc0"
ENGINE_2="lc0"

# threshholds
WIN_THRESHOLD = 100

# engine options
MULTIPV = 1
NODES = 1
BOOK_MIN_PLY = 4 

# initialize engines
engine_w = chess.engine.SimpleEngine.popen_uci(ENGINE_1)
engine_b = chess.engine.SimpleEngine.popen_uci(ENGINE_2)

# create game tree
game = chess.pgn.Game()
game.headers["Event"] = "Example"
game.headers["White"] = ENGINE_1
game.headers["Black"] = ENGINE_2
# init game node
node = None

# initialize board
board = chess.Board()

while not board.is_game_over():
    # if we're in the opening use the book
    if board.ply() <= BOOK_MIN_PLY-1:
        # init book
        book = None
        # load polyglot
        with chess.polyglot.open_reader("books/jbook.bin") as opening_book:
            if opening_book.get(board):
                book = opening_book.weighted_choice(board)
        
        # define and evaluate book move
        # chess.engine.Info(2) == cp score 
        if board.turn == chess.WHITE:
            result = engine_w.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV, root_moves=[book.move])
        else:
            result = engine_b.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV, root_moves=[book.move])

        opening_book.close()
    # else, use engine moves
    else:
        # define non-book move
        # chess.engine.Info(2) == cp score 
        if board.turn == chess.WHITE:
            result = engine_w.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV)
        else:
            result = engine_b.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV)

    # play the move
    board.push(result[0]['pv'][0])

    # record the move in the game tree
    if(node == None):
        node = game.add_main_variation(result[0]['pv'][0])
        
    else:
        node = node.add_main_variation(result[0]['pv'][0])

    # write score
    povscore = result[0]["score"]
    node.set_eval(povscore)

    # write result
    if board.is_game_over():
        # write checkmate
        if board.is_checkmate():
            if node.parent.turn() == chess.WHITE:
                game.headers['Result'] = "1-0"
            else:
                game.headers['Result'] = "0-1"

        # write non-checkmate eval
        else:
            score = povscore.relative.score()

            if (score <= WIN_THRESHOLD and score >= -WIN_THRESHOLD):
                game.headers['Result'] = "1/2-1/2"
            elif (score < -WIN_THRESHOLD):
                game.headers['Result'] = "0-1"
            elif (score > WIN_THRESHOLD):
                game.headers['Result'] = "1-0"

    # for debugging
    # print(game)

# exit engines
engine_w.quit()
engine_b.quit()

# write to a file
print(game, file=open("test.pgn", "w"), end="\n\n")
