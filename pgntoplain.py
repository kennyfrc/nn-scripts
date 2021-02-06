import chess.pgn
import argparse
import glob
import re
from typing import List
import pdb

def parse_result(result_str:str, board:chess.Board) -> int:
    if result_str == "1/2-1/2":
        return 0
    if result_str == "0-1":
        if board.turn == chess.WHITE:
            return -1
        else:
            return 1
    elif result_str == "1-0":
        if board.turn == chess.WHITE:
            return 1
        else:
            return -1
    else:
        print("illegal result", result_str)
        raise ValueError

def game_sanity_check(game: chess.pgn.Game) -> bool:
    if not game.headers["Result"] in ["1/2-1/2", "0-1", "1-0"]:
        print("invalid result", game.headers["Result"])
        return False
    return True
    
def parse_game(game: chess.pgn.Game, writer)->None:
    if not game_sanity_check(game):
        return

    result: str = game.headers["Result"]

    node = game.end()
    while node.move != None:
        move = node.move
        comment: str = node.comment
        writer.write("fen " + node.parent.board().fen() + "\n")
        writer.write("move " + str(move) + "\n")
        if node.parent.turn() == chess.WHITE:
            writer.write("score " + str(int(node.eval().pov(chess.WHITE).score(mate_score=15000)*2.08)) + "\n")
            writer.write("ply " + str(node.ply())+"\n")        
            writer.write("result " + str(parse_result(result, node.parent.board())) +"\n")
        else:
            writer.write("score " + str(int(node.eval().pov(chess.BLACK).score(mate_score=15000)*2.08)) + "\n")
            writer.write("ply " + str(node.ply())+"\n")        
            writer.write("result " + str(parse_result(result, node.parent.board())) +"\n")
        writer.write("e\n")
        node = node.parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pgn", type=str, required=True)
    parser.add_argument("--output", type=str, default="plain.txt")
    args = parser.parse_args()


    pgn_files: List[str] = glob.glob(args.pgn)
    pgn_files = sorted(pgn_files, key=lambda x:float(re.findall("-(\d+).pgn",x)[0] if re.findall("-(\d+).pgn",x) else 0.0))
    f = open(args.output, 'w')
    for pgn_file in pgn_files:
        print("parse", pgn_file)
        pgn_loader = open(pgn_file)
        game_count = 0
        while True:
            
            game = chess.pgn.read_game(pgn_loader)
            if game is None:
                break
            parse_game(game, f)
            game_count += 1
            print(f"parsed games:", game_count)
    f.close()
    
if __name__=="__main__":
    main()