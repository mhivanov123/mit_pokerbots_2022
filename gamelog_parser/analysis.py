import pandas as pd
from matplotlib import pyplot as plt
import sys

from round import Round, parse_gamelog

"""
    @param rounds list of round objs
    @param player number (0/1)
    This method is to be used for graphical interpretation of a gamelog
    currently tracks:
        bets: preflop bets, flop bets, turn bets, river bets
        total: total amount won by player
"""
def visual(rounds, player = 0):
    pfy, pfc = [], 'y-'
    fx, fy, fc = [], [], 'm-'
    tx, ty, tc = [], [], 'c-'
    rx, ry, rc = [], [], 'r-'
    deltay, deltac = [], 'g-'

    total = 0
    fig1 = plt.figure(figsize=(30,15))
    delta = fig1.add_subplot()
    fig2 = plt.figure(figsize=(30,15))
    bets = fig2.add_subplot()

    pot = 0
    for r in range(len(rounds)):
        total += rounds[r].awards[player]
        last = rounds[r].last_betting_round()
        pot = rounds[r].round_cost(0)
        pfy.append(pot)
        deltay.append(total)
        if 1 <= last:
            fx.append(r+1)
            fy.append(rounds[r].round_cost(1) - pot)
            pot = rounds[r].round_cost(1)
        if 2 <= last:
            tx.append(r+1)
            ty.append(rounds[r].round_cost(2) - pot)
            pot = rounds[r].round_cost(2)
        if 3 <= last:
            rx.append(r+1)
            ry.append(rounds[r].round_cost(3) - pot) 
        pot = 0
    bets.set_title('Bets')
    bets.plot(pfy, pfc, label = 'Pre-Flop')
    bets.plot(fx, fy, fc, label = 'Flop')
    bets.plot(tx, ty, tc, label = 'Turn')
    bets.plot(rx, ry, rc, label = 'River')

    delta.set_title('Total')
    delta.plot(deltay, deltac, label = 'Total')
    bets.legend()
    plt.show()
    

"""
    @return pandas dataframe with tabular analysis 
    @param rounds list of round objs
    @param player number (0/1)
    This method is to be used for tabular interpretation of a gamelog
    currently tracks: 
        rows: all rounds, pre-flop, flop, turn, river, player folds, other player folds, face-offs 
        cols: title, number of occurences, cummulative delta, avg delta, delta range, avg. # bet round, 
"""
def analysis(rounds, player = 0):
    # all irrellevant values can be filled with None
    NUM_ROWS = 8
    NUM_COLS = 6
    last = lambda round: round.last_betting_round()
    rows = {
        "names": ['All rounds', "pre-flop", "flop", "turn", 
            "river", "face-offs", "player folds","other player folds"],
        "identifiers": [
            lambda round: True,
            lambda round: True, # all rounds get to pre-flop,
            lambda round: True if 1 <= last(round) else False,
            lambda round: True if 2 <= last(round) else False,
            lambda round: True if 3 <= last(round) else False,
            lambda round: True if 4 == last(round) else False,
            lambda round: True if round.fold() == player else False,
            lambda round: True if round.fold() == (player+1)%2 else False
        ],
        "delta_rnd": [ # total cost to be considered (in rounds 
            4, 0, 1, 2, 3, 4, 4, 4] 
    }

    delta = lambda round, r: round.continue_cost(rows["delta_rnd"][r], player) # delta is the continue cost of interest
    avg = lambda avg0, sample, base0: (avg0*base0 + sample)/(base0+1)
    cols = {
        "names": [
            "Number Of Occurences", "cummulative Delta", "Avg. Delta", 
            "Min bet", "Max bet", "Avg. # Bet-Rounds"],
        "data": [[x for x in [0, 0, 0, 200, 0, 0]] for _ in range(NUM_ROWS)], # row, column: write in init val (x)
        "calculation": [  # online metric calculation::= lambda round, r, c: <...>
            # c is a known value in a sense, but it is easier/flexible for this as a param
            lambda round, r, c: cols["data"][r][c] + 1,
            lambda round, r, c: cols["data"][r][c] + delta(round, r),
            lambda round, r, c: avg(cols["data"][r][c], delta(round, r), cols["data"][r][0]),
            lambda round, r, c: min(abs(cols["data"][r][c]), abs(delta(round, r))),
            lambda round, r, c: max(abs(cols["data"][r][c]), abs(delta(round, r))),
            lambda round, r, c: avg(cols["data"][r][c], last(round), cols["data"][r][0]),
        ]
    }
    assert(NUM_ROWS == len(x) for x in rows.values()) # size assertion
    assert(NUM_COLS == len(x) for x in cols.values())

    # deltas
    for round in rounds:
        for r in range(NUM_ROWS):
            if rows["identifiers"][r](round):
                for c in range(NUM_COLS): # r corresponds with index of each var
                    cols["data"][r][c] = cols["calculation"][c](round, r, c)

    df = pd.DataFrame({cols["names"][c]: [row[c] for row in cols["data"]] for c in range(NUM_COLS)}, index = rows["names"])
    print(df)
    return df

if __name__ == '__main__':
    # run with path arg to gamelog: from gamelog_parser if interactive
    # from folder root if in terminal
    player = 0 # player 0 is challenger (always starts with button)
    log_path = "gamelogs/sadge07.txt"
    rounds = parse_gamelog(log_path)
    visual(rounds, player = player)
    analysis(rounds, player = player)
    
