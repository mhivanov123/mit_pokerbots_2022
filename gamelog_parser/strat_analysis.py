import gamelog_parser
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

def train(rounds):
    for round in rounds:
        for r in range(round.last_betting_round()):
            pass



if __name__ == '__main__':
    # run with path arg to gamelog: from gamelog_parser if interactive
    # from folder root if in terminal
    player = 0 # player 0 is challenger (always starts with button)
    log_path = "gamelogs/sadge07.txt"
    rounds = parse_gamelog(log_path)