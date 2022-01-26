'''
Simple example pokerbot, written in Python.
'''

from ast import Raise
from cgitb import small
from json import decoder
from re import L
import eval7
import random
import math
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot
import json

class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        self.score = 0
        self.round = 0

        self.position = True

        self.avg_bets = {0:0,3:0,4:0,5:0}
        self.streets = {0:0,3:0,4:0,5:0}

        self.raises = {0:0,3:0,4:0,5:0}
        self.calls = {0:0,3:0,4:0,5:0}
        self.reraises = {0:0,3:0,4:0,5:0}
        self.pfr = 0

        self.strengths = {0:0,3:0,4:0,5:0}
        self.strength = None

        self.opp_in = 0
        self.temp_street = 0
        self.temp_round = 0

        self.raised = False
        self.opp_raised = False

        self.limps = 0

        with open("./data/preflop_ev.json") as f:
            self.ev = json.load(f)
    
    def hand_format(self,hand):
        
        card_rank = {'2':1,'3':2,'4':3,'5':4,'6':5,'7':6,'8':7,'9':8,'T':9,'J':10,'Q':11,'K':12,'A':13}
        x = 's' if hand[0][1] == hand[1][1] else 'o'
        if card_rank[hand[0][0]] >= card_rank[hand[1][0]]:
            return hand[0][0]+hand[1][0]+x
        else:
            return hand[1][0]+hand[0][0]+x

    def calc_strength(self, hole, iters, community,swap_odd):
        ''' 
        Using MC with iterations to evalute hand strength 
        Args: 
        hole - our hole carsd 
        iters - number of times we run MC 
        community - community cards
        '''
        if len(community) == 0:
            return self.ev[self.hand_format(hole)]
            

        deck = eval7.Deck() # deck of cards
        hole_cards = [eval7.Card(card) for card in hole] # our hole cards in eval7 friendly format
        
        hole_cards = []
        for card in hole:
            temp = eval7.Card(card)
            deck.cards.remove(temp)
            if random.random() < swap_odd:
                deck.shuffle()
                replace = deck.peek(1)[0]
                hole_cards.append(replace)
            else:
                hole_cards.append(temp)


        if community != []:
            community_cards = [eval7.Card(card) for card in community]
            for card in community_cards: #removing the current community cards from the deck
                deck.cards.remove(card)

        
        score = 0
        num_ignored = 0
        hand_samples = 0

        for _ in range(iters): # MC the probability of winning
            deck.shuffle()

            _COMM = 5 - len(community)
            _OPP = 2 

            draw = deck.peek(_COMM + _OPP)  
            
            opp_hole = draw[:_OPP]
            alt_community = draw[_OPP:]

            
            if community == []:
                our_hand = hole_cards  + alt_community
                opp_hand = opp_hole  + alt_community
            else: 

                our_hand = hole_cards + community_cards + alt_community
                opp_hand = opp_hole + community_cards + alt_community


            our_hand_value = eval7.evaluate(our_hand)
            opp_hand_value = eval7.evaluate(opp_hand)

            opp_hand_type = eval7.handtype(opp_hand_value)

            if our_hand_value > opp_hand_value:
                card_rank = {0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8', 7: '9', 8: 'T', 9: 'J', 10: 'Q', 11: 'K', 12: 'A'}
                card_suit = {0:'c',1:'d',2:'h',3:'s',}
                
                #0.4 can be adjusted to lower, but 0.4 matches our preflop fold decision
                if 0 < len(community) < 5 and self.ev[self.hand_format([card_rank[x.rank]+card_suit[x.suit] for x in opp_hole])] < 0.4:
                    num_ignored += 1
                    score -= 2

                if opp_hand_type == 'High Card' and len(community) == 5:
                    num_ignored+=1
                    score-=2

                score += 2 

            if our_hand_value == opp_hand_value:
                score += 1
                hand_samples+=1 

            else:
                score += 0
                hand_samples+=1        

        hand_strength = score/(2*(iters-num_ignored)) # win probability
        

        return hand_strength
    
    def low_pair(self,hand_types):
        """
        will tell us if we lose to a higher pair
        """
        
        max = (0,0)
        for type in hand_types:
            if hand_types[type] > max[1]:
                max = (type, hand_types[type])
            
        if max[0] == 'Pair':
            return 0.5
        else:
            return 1
    
    def all_hands(self,hole,community):
        pass

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        my_cards = round_state.hands[active]  # your cards
        big_blind = bool(active)  # True if you are the big blind

        self.round += 1 #keep track of round number

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        street = previous_state.street  # 0, 3, 4, or 5 representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed

        if self.raised and opp_cards:
            self.calls[5]+=1

        if self.raised and not opp_cards:
            #folded on river
            pass
        
        self.raised = False
        self.opp_raised = False

        self.score += my_delta #keep track of score
        
    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        street = round_state.street  # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.deck[:street]  # the board cards
        my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        my_stack = round_state.stacks[active]  # the number of chips you have remaining
        opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        net_upper_raise_bound = round_state.raise_bounds()
        stacks = [my_stack, opp_stack] #keep track of our stacks

        net_cost = 0
        my_action = None

        min_raise, max_raise = round_state.raise_bounds()
        pot_total = my_contribution + opp_contribution

        #######STATS#######
        #calculate vpip here
        #keep track of average number of chips in pot during all game stages
        if self.temp_street < street:
            self.streets[self.temp_street] += 1
            self.strength = None

            if self.raised:
                self.calls[self.temp_street] += 1
                self.raised = False

            self.opp_raised = False
            self.temp_street = street
           
        elif self.temp_street >= street and self.temp_round < self.round:
            self.streets[self.temp_street] += 1
            self.temp_street = street
            self.temp_round = self.round
            self.raised = False
            self.strength = None

        if street == 0 and continue_cost > SMALL_BLIND:
            self.pfr += 1

        if continue_cost > 0 and continue_cost > SMALL_BLIND and not self.opp_raised:
            self.raises[street] += 1
            self.opp_raised = True

        if self.raised and continue_cost > 0 and self.temp_street == street:
            self.reraises[street] += 1

        if self.round > 25:
            VPIP = (self.raises[street] + self.calls[street])/self.streets[street]
            pfr = self.pfr/self.round

            '''print(str(self.round)+'--' +'vpip: '+str(VPIP))
            print('pfr: ' + str(pfr))'''

        reraise = 0.1 
        AF = 2

        if self.round > 25:
            reraise = self.reraises[street]/self.streets[street]
            
        if self.round > 100:
            AF = self.raises[street]/max(self.calls[street],1)

        if street == 0 and CheckAction in legal_actions:
            self.limps += 1

        ###################
        # remove cards that would be folded preflop from strength calc
        #######STRENGTH#######
        _MONTE_CARLO_ITERS = 250
        if street <3:
            strength = self.calc_strength(my_cards, _MONTE_CARLO_ITERS,[],0.1)
        elif street == 3:
            strength = self.calc_strength(my_cards, _MONTE_CARLO_ITERS,board_cards,0.05)
            
        else:
            strength = self.calc_strength(my_cards, _MONTE_CARLO_ITERS, board_cards, 0)

        if not self.strength:
            self.strength = strength
            self.strengths[street] += strength

        #####################
        #print(str(self.round) + '   '  +str(street)+': '+str(strength))

        if self.round == 999:
            for street_ in self.strengths:
                print(self.streets)
                print(str(street_)+': ' + str(self.strengths[street_]/self.streets[street_]))

        #######SCARY#######
        _SCARY = 0
        if continue_cost > 10:
            _SCARY = 0.1
        if continue_cost > 20: 
            _SCARY = .2
        if continue_cost > 50: 
            _SCARY = 0.35
        ###################

        #######INSTA_FOLD#######
        #if far enough ahead, start folding
        fold_cost = BIG_BLIND*math.ceil((NUM_ROUNDS - self.round)/2) + SMALL_BLIND*math.ceil((NUM_ROUNDS - self.round)/2)
        #TURN THIS ON BEFORE SUBMITTING BOT
        '''if self.score - fold_cost > 2:
            return CheckAction() if CheckAction in legal_actions else FoldAction()'''
        ########################

        #######PREFLOP_PARAMETERS######
        preflop_3bet = 0.55 #what should strength be to 3bet
        preflop_raise = 0.4 #what should strength be to raise a button call
        preflop_opp_3bet_call = 0.6 #what should strength be to call op 3bet
        preflop_4bet = 0.75 # what should strength be to 4bet
        preflop_fold = 0.4 #what should strength be to fold on the button
        preflop_standard_bet = 7 
        ###############################

        #######FT_PARAMETERS#######
        ft_strong_raise = 0.6
        ft_mid_raise = 0.5
        ft_call = 0.6
        ft_op_strong_raise = 0.65
        ft_op_mid_raise = 0.55
        ###########################
        '''if street == 4:
            ft_strong_raise = 0.7
            ft_mid_raise = 0.6
            ft_call = 0.6
            ft_op_strong_raise = 0.75
            ft_op_mid_raise = 0.65'''
        
        if street == 5:
            ft_strong_raise = 0.8
            ft_mid_raise = 0.7
            ft_call = 0.6
            ft_op_strong_raise = 0.85
            ft_op_mid_raise = 0.75

        
        #######RIVER_PARAMETERS######
        river_3bet = 0.75 #what should strength be to 3bet
        river_raise = 0.7 #what should strength be to raise on button or after opp check
        river_call = 0.65 #what should strength be to call an opp raise
        river_3bet_call = 0.8
        river_4bet = 0.8 #what should strength be to 4bet
        ###############################

        #######PREFLOP_ACTION#######
        
        if street == 0:
            pot_odds = continue_cost/(pot_total + continue_cost)

            post_rand = random.uniform(0.3,0.6) 
            raise_amount = int(my_pip + continue_cost + post_rand*(pot_total + continue_cost))
            
            raise_amount = max([min_raise, raise_amount])
            raise_amount = min([max_raise, raise_amount])

            if my_pip == BIG_BLIND:

                self.position = False

                if continue_cost > 0:

                    #we will 3bet
                    if RaiseAction in legal_actions and strength > preflop_3bet and random.random() < 0.5:
                        my_action =  RaiseAction(raise_amount)

                    elif CallAction in legal_actions and strength > preflop_raise:
                        my_action =  CallAction()
                    
                    else:
                        my_action =  FoldAction()
                    
                elif RaiseAction in legal_actions and random.random() < 0.8 and strength > preflop_raise:
                    my_action =  RaiseAction(preflop_standard_bet)

                elif CheckAction in legal_actions:
                    my_action =  CheckAction()

            elif my_pip == SMALL_BLIND:
                self.position = True

                if strength < preflop_fold:
                    my_action =  FoldAction()
                
                elif RaiseAction in legal_actions:
                    my_action =  RaiseAction(preflop_standard_bet)

                else:
                    my_action =  CallAction()
                    
            #opponent 3bet or 4bet
            elif self.raised and continue_cost > 0:

                if strength > preflop_4bet and RaiseAction in legal_actions and random.random() < 0.1:
                    my_action =  RaiseAction(raise_amount)

                elif (CallAction in legal_actions and (continue_cost <= my_stack)):
                    my_action =  CallAction()

                else:
                    my_action = FoldAction()

        ############################
        
        #######FLOP_ACTION#######

        ########################

        #######RIVER_ACTION#######

        elif street == 5:
            post_rand = random.uniform(0.5,1) 
            raise_amount = int(my_pip + continue_cost + post_rand*(pot_total + continue_cost))

            # ensure raises are legal
            raise_amount = max([min_raise, raise_amount])
            raise_amount = min([max_raise, raise_amount])

            #will tell us to raise unless we can't
            if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
                temp_action = RaiseAction(raise_amount)
            elif (CallAction in legal_actions and (continue_cost <= my_stack)):
                temp_action = CallAction()
            elif CheckAction in legal_actions:
                temp_action = CheckAction()
            else:
                temp_action = FoldAction()

            if continue_cost > 0:
                pot_odds = continue_cost/(pot_total + continue_cost)

                #opponent reraised
                if self.raised:
        
                    #potential 4bet
                    if random.random() < 0.1 and strength > river_4bet: 
                            my_action = temp_action
                    elif strength > river_3bet_call and CallAction in legal_actions and (continue_cost <= my_stack): 
                            my_action = CallAction()
                    else:
                        my_action = FoldAction()
                            
                else:
                    if strength > river_call: #reraise NEED TO INCLUDE METRIC ON HOW OFTEN THEY CALL 3BETS
                        #3 BET
                        if strength > river_3bet and random.random() < 0.3:
                            my_action = temp_action
                        else:
                            my_action = CallAction()

                    else: #negative EV
                        my_action = FoldAction()
            
            else:
                if self.position:
                    if strength > river_raise:
                        if random.random() < 0.5:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                    else:
                        my_action = CheckAction()

                else:
                    if strength > river_4bet:
                        if random.random() < 0.6:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                    else:
                        my_action = CheckAction()
            
        ##########################

        elif street == 6:
            # raise logic
            post_rand = random.uniform(0.5,1) 
            raise_amount = int(my_pip + continue_cost + post_rand*(pot_total + continue_cost))

            # ensure raises are legal
            raise_amount = max([min_raise, raise_amount])
            raise_amount = min([max_raise, raise_amount])

            #will tell us to raise unless we can't
            if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
                temp_action = RaiseAction(raise_amount)
            elif (CallAction in legal_actions and (continue_cost <= my_stack)):
                temp_action = CallAction()
            elif CheckAction in legal_actions:
                temp_action = CheckAction()
            else:
                temp_action = FoldAction() 

            pot_odds = continue_cost/(pot_total + continue_cost)

            #opp acts first
            if self.position:
                #opp raised
                if continue_cost > 0:
                    if strength > ft_strong_raise:
                        if random.random() < 0.3:
                            my_action = temp_action
                        else:
                            my_action = CallAction()
                    elif strength > ft_mid_raise or strength > pot_odds + _SCARY:
                        if random.random() < 0.1:
                            my_action = temp_action
                        else:
                            my_action = CallAction()

                    else: #negative EV
                        my_action = FoldAction()

                #opp checked
                else:
                    #keep track of opponent checks and add constraints here
                    if strength > ft_op_strong_raise:
                        if random.random() < 0.8:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()

                    elif strength > ft_op_mid_raise or strength > pot_odds + _SCARY:
                        if random.random() < 0.6:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()

                    else:
                        if random.random() < 0.1 and strength > 0.6:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()

                    my_action = CheckAction()
                
            #we act first
            else:
                #opp reraised
                if continue_cost > 0:
                    #we will call every time because we raise with strength > 0.7
                    if CallAction in legal_actions and (continue_cost <= my_stack) and strength >= pot_odds + _SCARY:
                        my_action = CallAction()
                
                    else:
                        my_action = FoldAction()
                #we act first
                else:
                    if strength > ft_strong_raise:
                        if random.random() < 0.8:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                    
                    if strength > ft_mid_raise or strength > pot_odds + _SCARY:
                        if random.random() < 0.4:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                    

                    else:
                        my_action = CheckAction()


        else:
        
            # raise logic
            post_rand = random.uniform(0.5,1) 
            raise_amount = int(my_pip + continue_cost + post_rand*(pot_total + continue_cost))

            # ensure raises are legal
            raise_amount = max([min_raise, raise_amount])
            raise_amount = min([max_raise, raise_amount])

            #will tell us to raise unless we can't
            if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
                temp_action = RaiseAction(raise_amount)
            elif (CallAction in legal_actions and (continue_cost <= my_stack)):
                temp_action = CallAction()
            elif CheckAction in legal_actions:
                temp_action = CheckAction()
            else:
                temp_action = FoldAction() 

            pot_odds = continue_cost/(pot_total + continue_cost)

            #opp acts first
            if self.position:
                #opp raised
                if continue_cost > 0:
                    if strength > ft_strong_raise:
                        if random.random() < 0.5:
                            my_action = temp_action
                        else:
                            my_action = CallAction()
                    elif strength > ft_mid_raise and strength > pot_odds + _SCARY:
                        if random.random() < 0.1:
                            my_action = temp_action
                        else:
                            my_action = CallAction()

                    else: #negative EV
                        my_action = FoldAction()

                #opp checked
                else:
                    #keep track of opponent checks and add constraints here
                    if strength > ft_strong_raise:
                        if random.random() < 0.8:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()

                    elif strength > ft_mid_raise:
                        if random.random() < 0.6:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()

                    else:
                        if random.random() < 0.1 and strength > 0.6:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                
            #we act first
            else:
                #opp reraised
                if continue_cost > 0:
                    #we will call every time because we raise with strength > 0.7
                    if CallAction in legal_actions and (continue_cost <= my_stack) and strength >= ft_mid_raise:# 
                        my_action = CallAction()
                
                    else:
                        my_action = FoldAction()
                #we act first
                else:
                    if strength > ft_op_strong_raise:
                        if random.random() < 0.5:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                    
                    elif strength > ft_op_mid_raise:
                        if random.random() < 0.2:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                    

                    else:
                        my_action = CheckAction()

        if my_action != CheckAction() or my_action != CallAction() or my_action != FoldAction():
            self.raised = True
        else:
            self.raised = False

        return my_action

if __name__ == '__main__':
    run_bot(Player(), parse_args())
"""
elif street == 3:
            # raise logic
            post_rand = random.uniform(0.5,1) 
            raise_amount = int(my_pip + continue_cost + post_rand*(pot_total + continue_cost))

            # ensure raises are legal
            raise_amount = max([min_raise, raise_amount])
            raise_amount = min([max_raise, raise_amount])

            #will tell us to raise unless we can't
            if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
                temp_action = RaiseAction(raise_amount)
            elif (CallAction in legal_actions and (continue_cost <= my_stack)):
                temp_action = CallAction()
            elif CheckAction in legal_actions:
                temp_action = CheckAction()
            else:
                temp_action = FoldAction() 

            pot_odds = continue_cost/(pot_total + continue_cost)

            #opp acts first
            if self.position:
                #opp raised
                if continue_cost > 0:
                    if strength > ft_strong_raise:
                        if random.random() < 0.6:
                            my_action = temp_action
                        else:
                            my_action = CallAction()
                    elif strength > ft_mid_raise or strength > pot_odds + _SCARY:
                        if random.random() < 0.4:
                            my_action = temp_action
                        else:
                            my_action = CallAction()

                    else: #negative EV
                        my_action = FoldAction()

                #opp checked
                else:
                    #keep track of opponent checks and add constraints here
                    if strength > ft_op_strong_raise:
                        if random.random() < 0.8:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()

                    elif strength > ft_op_mid_raise or strength > pot_odds + _SCARY:
                        if random.random() < 0.6:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()

                    else:
                        if random.random() < 0.1 and strength > 0.5:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                
            #we act first
            else:
                #opp reraised
                if continue_cost > 0:
                    #we will call every time because we raise with strength > 0.7
                    if CallAction in legal_actions and (continue_cost <= my_stack) and strength >= pot_odds + _SCARY:
                        my_action = CallAction()
                
                    else:
                        my_action = FoldAction()
                #we act first
                else:
                    if strength > ft_strong_raise:
                        if random.random() < 0.5:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                    
                    if strength > ft_mid_raise:
                        if random.random() < 0.2:
                            my_action = temp_action
                        else:
                            my_action = CheckAction()
                    

                    else:
                        my_action = CheckAction()
"""

'''
if continue_cost > 0:
                
                pot_odds = continue_cost/(pot_total + continue_cost)

                #opponent reraised
                if self.raised:
                    
                    if strength > ft_strong_raise:
                        if random.random() < 0.2:
                            my_action = temp_action

                        elif CallAction in legal_actions and (continue_cost <= my_stack):
                            my_action = CallAction()

                    elif strength >= pot_odds + _SCARY: # nonnegative EV decision

                        if strength > ft_mid_raise and random.random() < 0.25: 
                            my_action = temp_action
                        elif strength > ft_call and CallAction in legal_actions and (continue_cost <= my_stack): 
                            my_action = CallAction()
                        else:
                            my_action = FoldAction()
                    
                    else: #negative EV
                        my_action = FoldAction()
                            
                else:
                    if AF < 2:
                        if strength >= pot_odds + _SCARY: #reraise NEED TO INCLUDE METRIC ON HOW OFTEN THEY CALL 3BETS
                            #3 BET
                            if strength > ft_strong_raise and random.random() < 0.3:
                                my_action = temp_action
                            elif strength > ft_call: 
                                my_action = CallAction()
                            else:
                                my_action = FoldAction()
                        
                        else: #negative EV
                            my_action = FoldAction()

                    else:
                        if strength >= pot_odds + _SCARY: #reraise NEED TO INCLUDE METRIC ON HOW OFTEN THEY CALL 3BETS
                            #3 BET
                            if strength > ft_mid_raise and random.random() < 0.5:
                                my_action = temp_action
                            elif strength > ft_call: 
                                my_action = CallAction()
                            else:
                                my_action = FoldAction()
                        
                        else: #negative EV
                            my_action = FoldAction()
            
            else:
                if strength > ft_strong_raise:
                    if random.random() < 0.75:
                        my_action = temp_action
                    else:
                        my_action = CheckAction()

                elif strength > ft_mid_raise:
                    if random.random() < 0.5:
                        my_action = temp_action
                    else:
                        my_action = CheckAction()

                else:
                    if random.random() < 0.1 and strength > 0.5:
                        my_action = temp_action
                    else:
                        my_action = CheckAction()
'''


