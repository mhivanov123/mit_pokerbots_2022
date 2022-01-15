'''
Simple example pokerbot, written in Python.
'''

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

        self.avg_bets = {0:0,3:0,4:0,5:0}
        self.streets = {0:0,3:0,4:0,5:0}

        self.raises = {0:0,3:0,4:0,5:0}
        self.calls = {0:0,3:0,4:0,5:0}
        self.reraises = {0:0,3:0,4:0,5:0}

        self.opp_in = 0
        self.temp_street = 0
        self.temp_round = 0

        self.raised = False

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

        hand_types = 0

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

            our_hand_type = eval7.handtype(our_hand_value)
            opp_hand_type = eval7.handtype(opp_hand_value)

            if our_hand_value > opp_hand_value:
                score += 2 

            if our_hand_value == opp_hand_value:
                score += 1 

            else:
                #will tell us if we are beaten by a higher hand
                if opp_hand_type == our_hand_type:
                    hand_types += 1
                
                score += 0        

        hand_strength = score/(2*iters) # win probability 

        return (hand_strength,hand_types/iters)
    
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

        if continue_cost > 0 and continue_cost > SMALL_BLIND:
            self.raises[street] += 1

        if self.raised and continue_cost > 0 and self.temp_street == street:
            self.reraises[street] += 1

        #keep track of average number of chips in pot during all game stages
        if self.temp_street < street:
            self.streets[self.temp_street] += 1

            if self.raised:
                self.calls[self.temp_street] += 1
                self.raised = False

            self.temp_street = street
           
        elif self.temp_street >= street and self.temp_round < self.round:
            self.streets[self.temp_street] += 1
            self.temp_street = street
            self.temp_round = self.round
            self.raised = False

        
        VPIP = (self.raises[0] + self.calls[0])/self.round
        AF =  self.raises[street]/max(self.calls[street],1)
        reraise = 0.1 

        if self.round > 25:
            reraise = self.reraises[street]/self.streets[street]
        

        if street == 0 and CheckAction in legal_actions:
            self.limps += 1

        ###################

        #######STRENGTH#######
        _MONTE_CARLO_ITERS = 250
        if street <3:
            strength = self.calc_strength(my_cards, _MONTE_CARLO_ITERS,[],0.1)
        elif street == 3:
            MC = self.calc_strength(my_cards, _MONTE_CARLO_ITERS,board_cards,0.05)
            strength = MC[0]
            beats_us = MC[1]
        else:
            MC = self.calc_strength(my_cards, _MONTE_CARLO_ITERS, board_cards, 0)
            strength = MC[0]
            beats_us = MC[1]
        #####################

        #######SCARY#######
        _SCARY = 0
        if continue_cost > 6:
            _SCARY = 0.1
        if continue_cost > 15: 
            _SCARY = .2
        if continue_cost > 50: 
            _SCARY = 0.35
        ###################

        #######INSTA_FOLD#######

        #if far enough ahead, start folding
        fold_cost = BIG_BLIND*math.ceil((NUM_ROUNDS - self.round)/2) + SMALL_BLIND*math.ceil((NUM_ROUNDS - self.round)/2)
        if self.score - fold_cost > 2:
            return CheckAction() if CheckAction in legal_actions else FoldAction()
        
        ########################

        #######NEAR_LOSS#######
        '''max_loss = 1
        if self.score < 0:
            max_loss = (fold_cost + self.score)/200

        if max_loss < 0.1:
            if strength > 0.8:
                strength = 10
            else:
                strength = 0
        elif max_loss < 0.5:
            if strength > 0.8:
                strength = 10
            elif strength > 0.6:
                strength += 0.1
            else:
                strength = 0
        elif max_loss < 1:
            if strength > 0.6:
                strength += 0.1
            else:
                strength = 0'''
        #########################

        #######PREFLOP_ACTION#######
        
        if street == 0:
            pot_odds = continue_cost/(pot_total + continue_cost)

            if my_pip == BIG_BLIND:

                if continue_cost > 0:
                    
                    raise_amount = int(my_pip + continue_cost + 0.4*(pot_total + continue_cost))
                    raise_amount = max([min_raise, raise_amount])
                    raise_amount = min([max_raise, raise_amount])

                    #we will 3bet
                    if RaiseAction in legal_actions and strength > 0.6 and random.random() < 0.5:
                        my_action =  RaiseAction(raise_amount)

                    elif CallAction in legal_actions and strength > pot_odds + _SCARY:
                        my_action =  CallAction()
                    
                    else:
                        my_action =  FoldAction()
                    
                elif RaiseAction in legal_actions and random.random() < 0.5 and strength > 0.5:
                    my_action =  RaiseAction(7)

                elif CheckAction in legal_actions:
                    my_action =  CheckAction()

            elif my_pip == SMALL_BLIND:
                if strength < 0.4:
                    my_action =  FoldAction()
                
                elif RaiseAction in legal_actions and random.random() < strength:
                    my_action =  RaiseAction(7)

                else:
                    my_action =  CallAction()
                    
            #opponent 3bet or 4bet
            elif self.raised and continue_cost > 0:
                if strength > 0.6 or strength > pot_odds + _SCARY:
                    my_action =  CallAction()
                else:
                    my_action = FoldAction()

        ############################

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
                    #on river we only raise with strength > 0.8

                    #they 3bet with good cards
                    if reraise < 0.1:
                        if strength > 0.8:
                            #potential 4bet
                            if random.random() < 0.25:
                                my_action = temp_action

                            elif CallAction in legal_actions and (continue_cost <= my_stack): 
                                my_action = CallAction()
                            
                        else:
                            my_action = FoldAction()
                    
                    #they're looser with 3bets
                    else:
                        #potential 4bet
                        if random.random() < strength: 
                                my_action = temp_action
                        elif CallAction in legal_actions and (continue_cost <= my_stack): 
                                my_action = CallAction()
                            
                else:
                    if AF < 2: #if they don't raise very often
                        if strength >= pot_odds + _SCARY: #reraise NEED TO INCLUDE METRIC ON HOW OFTEN THEY CALL 3BETS
                            #3 BET
                            if strength > 0.8 and random.random() < 0.3:
                                my_action = temp_action
                            elif strength > 0.75: 
                                my_action = CallAction()
                            else:
                                my_action = FoldAction()
                        
                        else: #negative EV
                            my_action = FoldAction()

                    else:
                        if strength >= pot_odds + _SCARY: #reraise NEED TO INCLUDE METRIC ON HOW OFTEN THEY CALL 3BETS
                            #3 BET
                            if strength > 0.7 and random.random() < 0.3:
                                my_action = temp_action
                            elif strength > 0.5: 
                                my_action = CallAction()
                            else:
                                my_action = FoldAction()
                        
                        else: #negative EV
                            my_action = FoldAction()
            
            else:
                if strength > 0.8:
                    if random.random() < 0.75:
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

            if continue_cost > 0:
                
                pot_odds = continue_cost/(pot_total + continue_cost)

                #opponent reraised
                if self.raised:
                    #they 3bet with good cards
                    if reraise < 0.1:
                        if strength > 0.8:
                            #potential 4bet
                            if random.random() < 0.25:
                                my_action = temp_action

                            elif CallAction in legal_actions and (continue_cost <= my_stack): 
                                my_action = CallAction()
                            
                        else:
                            my_action = FoldAction()
                    
                    #they're looser with 3bets
                    else:
                        if strength > 0.8:
                            if random.random() < 0.25:
                                my_action = temp_action

                            elif CallAction in legal_actions and (continue_cost <= my_stack):
                                my_action = CallAction()

                        elif strength >= pot_odds + _SCARY: # nonnegative EV decision

                            if strength > 0.6 and random.random() < 0.25: 
                                my_action = temp_action
                            elif strength > 0.55 and CallAction in legal_actions and (continue_cost <= my_stack): 
                                my_action = CallAction()
                            else:
                                my_action = FoldAction()
                        
                        else: #negative EV
                            my_action = FoldAction()
                            
                else:
                    if AF < 2:
                        if strength >= pot_odds + _SCARY: #reraise NEED TO INCLUDE METRIC ON HOW OFTEN THEY CALL 3BETS
                            #3 BET
                            if strength > 0.8 and random.random() < 0.3:
                                my_action = temp_action
                            elif strength > 0.5: 
                                my_action = CallAction()
                            else:
                                my_action = FoldAction()
                        
                        else: #negative EV
                            my_action = FoldAction()

                    else:
                        if strength >= pot_odds: #reraise NEED TO INCLUDE METRIC ON HOW OFTEN THEY CALL 3BETS
                            #3 BET
                            if strength > 0.7 and random.random() < 0.3:
                                my_action = temp_action
                            elif strength > 0.5: 
                                my_action = CallAction()
                            else:
                                my_action = FoldAction()
                        
                        else: #negative EV
                            my_action = FoldAction()
            
            else:
                if strength > 0.8:
                    if random.random() < 0.75:
                        my_action = temp_action
                    else:
                        my_action = CheckAction()

                elif strength > 0.6:
                    if random.random() < 0.5:
                        my_action = temp_action
                    else:
                        my_action = CheckAction()

                else:
                    if random.random() < 0.1:
                        my_action = temp_action
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
if strength >= pot_odds: # nonnegative EV decision
                    if strength > 0.5 and random.random() < strength: 
                        my_action = temp_action
                    else: 
                        my_action = CallAction()
                
                else: #negative EV
                    my_action = FoldAction()
                    
            else: # continue cost is 0  
                if strength > 0.6: 
                    my_action = temp_action
                else: 
                    my_action = CheckAction()

"""

"""
        ########FLOP_ACTION#######

        elif street == 3:
            post_rand = random.uniform(0.5,1)
            raise_amount = int(my_pip + continue_cost + post_rand*(pot_total + continue_cost))
            raise_amount = max([min_raise, raise_amount])
            raise_amount = min([max_raise, raise_amount])

            if continue_cost > 0:
                #if opp reraised
                if self.raised:
                    reraise_p = self.reraises[street]/self.streets[street]
                    if strength > 0.65:
                        if random.random() < 0.1:
                            my_action = RaiseAction(raise_amount)
                        else:
                            my_action = CallAction()

                    elif reraise_p > 0.2:
                        my_action = CallAction()

                    else:
                        my_action = FoldAction()

                
                #opp was first to raise
                else:
                    if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
                        temp_action = RaiseAction(raise_amount)
                    elif (CallAction in legal_actions and (continue_cost <= my_stack)):
                        temp_action = CallAction()
                    elif CheckAction in legal_actions:
                        temp_action = CheckAction()
                    else:
                        temp_action = FoldAction()

                    strength = max(0, strength - _SCARY)
                    pot_odds = continue_cost/(pot_total + continue_cost)

                    if strength >= pot_odds: # nonnegative EV decision
                        if strength > 0.5 and random.random() < strength: 
                            my_action = temp_action
                        else: 
                            my_action = CallAction()
                
                    else: #negative EV
                        my_action = FoldAction()


            else:

                if strength > 0.5 and random.random() < 0.75:
                    return RaiseAction(raise_amount)
                else:
                    return CheckAction()

        ##########################

        #######RIVER_ACTION#######
        elif street >= 4:
            post_rand = random.uniform(0.5,1)
            raise_amount = int(my_pip + continue_cost + post_rand*(pot_total + continue_cost))
            raise_amount = max([min_raise, raise_amount])
            raise_amount = min([max_raise, raise_amount])

            #strength *= self.low_pair(beats_us)

            if continue_cost > 0:
                #opp reraised
                if self.raised:
                    if strength > 0.8 and RaiseAction in legal_actions:
                        my_action = RaiseAction(max_raise)
                    elif strength > 0.6:
                        my_action = CallAction()
                    else:
                        my_action = FoldAction()

                else:
                    if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
                        temp_action = RaiseAction(raise_amount)
                    elif (CallAction in legal_actions and (continue_cost <= my_stack)):
                        temp_action = CallAction()
                    elif CheckAction in legal_actions:
                        temp_action = CheckAction()
                    else:
                        temp_action = FoldAction()

                    strength = max(0, strength - _SCARY)
                    pot_odds = continue_cost/(pot_total + continue_cost)

                    if strength > 0.75: #going to reraise
                        my_action = RaiseAction(raise_amount)

                    if strength >= pot_odds: # nonnegative EV decision
                        if strength > 0.5 and random.random() < strength: 
                            my_action = temp_action
                        else: 
                            my_action = CallAction()
                
                    else: #negative EV
                        my_action = FoldAction()

            else:
                if strength > 0.9:
                    if random.random() < 0.5 and RaiseAction in legal_actions:
                        my_action = RaiseAction(max_raise)
                    elif RaiseAction in legal_actions:
                        my_action = RaiseAction(raise_amount)
                elif strength > 0.5:
                    if random.random() < 0.2:
                        my_action = CheckAction()
                    elif RaiseAction in legal_actions:
                        my_action = RaiseAction(raise_amount)
                    else:
                        my_action = CheckAction()

                else:
                    my_action = CheckAction()
                    
        ##########################
        


"""