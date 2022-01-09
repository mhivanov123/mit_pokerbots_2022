import numpy as np
import pandas as pd
from config import NUM_ROUNDS
from gamelog_parser import round, parse_gamelog


"""
    @return the amount which the player chooses to bet
        indicated by the action given
    @param action
    @param ccost, continue cost for the betting round
    * ccost only valid for raise or big blind response
    * if a bigblind call enter 2, else raise amount
"""
def action_interpretter(action, ccost = 0):
    if action == "F":
        return 0
    elif action == "K":
        return 0
    elif action == "C": 
        return ccost
    elif action[0] == "R":
        return int(action[1:])

# make bet analysis' independent of each other
# train model on independent betting round strats and overall strat. 


def data_clean(rounds):
    # get info for each of the betting rounds if applicable
    inputs = {
        "pot":
        "pod odds":
        "win perc":
        "continue cost":
        "prev action type":
    }

    NUM_INPUT = 5
    NUM_BET = 4

    data = np.full((len(rounds), NUM_BET, NUM_INPUT), np.nan)  # filled with np.nan must remove for analysis
    for round in rounds:
        for r in range(round.last_betting_round()):
            # will consider amount bet as output
            # will interpret ... as input:
            # pot amount, pot odds, W%, continue cost, previous action type




if __name__ == '__main__':
    # run with path arg to gamelog: from gamelog_parser if interactive
    # from folder root if in terminal
    player = 0 # player 0 is challenger (always starts with button)
    log_path = "gamelogs/sadge07.txt"
    rounds = parse_gamelog(log_path)
    pd.DataFrame()