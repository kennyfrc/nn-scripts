import chess
import chess.pgn
import chess.engine

# define engines
ENGINE_1="stockfish"
ENGINE_2="stockfish"

# games pgn
games = []

# threshholds
WIN_THRESHOLD = 150

# initialize engines
engine_w = chess.engine.SimpleEngine.popen_uci(ENGINE_1)
engine_b = chess.engine.SimpleEngine.popen_uci(ENGINE_2)

# create pgn
game = chess.pgn.Game()
game.headers["Event"] = "Example"
game.headers["White"] = ENGINE_1
game.headers["Black"] = ENGINE_2
node = ""

# initialize board
board = chess.Board()
while not board.is_game_over():

    # define move 
    # chess.engine.Info(2) == cp score 
    if board.turn == chess.WHITE:
        result = engine_w.play(board, chess.engine.Limit(nodes=1), info=chess.engine.Info(2))
    else:
        result = engine_b.play(board, chess.engine.Limit(nodes=1), info=chess.engine.Info(2))

    # play the move
    board.push(result.move)

    # record the move in the pgn
    if(node == ""):
        node = game.add_main_variation(result.move)
        
    else:
        node = node.add_main_variation(result.move)

    # write score
    povscore = result.info["score"]
    node.set_eval(povscore)

    # write result
    if board.is_game_over():
        # write checkmate
        if board.is_checkmate():
            if node.parent.turn() == chess.WHITE:
                game.headers['Result'] = "1-0"
            else:
                game.headers['Result'] = "0-1"

        # non-checkmate situations
        else:
            score = povscore.relative.score()

            if (score <= WIN_THRESHOLD and score >= -WIN_THRESHOLD):
                game.headers['Result'] = "1/2-1/2"
            elif (score < -WIN_THRESHOLD):
                game.headers['Result'] = "0-1"
            elif (score > WIN_THRESHOLD):
                game.headers['Result'] = "1-0"

# quit engines
engine_w.quit()
engine_b.quit()

# write to a file
print(game, file=open("test.pgn", "w"), end="\n\n")
