import math
import os
import random
import time

import format
import model


class Bot:

    def __init__(self, guild_id):
        self.model = model.Model()

        self.channel_id = ''
        self.guild_id = guild_id

        self.random_wait = 5
        self.msgs_wait = 10
        self.mention_wait = 2
        self.rant_size = 10
        self.rant_chance = 5

        self.can_generate_unique_takes = False
        self.max_previous_takes = 20
        self.previous_takes = []

        self.enabled = True
        self.learn = True
        self.warlock_only = False
        self.training_root_dir = 'train'
        self.current_data_set = 'none'

        self.ready_for_mention = True
        self.time_of_mention = time.time() - self.mention_wait*60
        self.ready_for_random = True
        self.time_of_random = time.time() - self.random_wait*60
        self.msgs_waited = 0
        self.previous_messages = []

    def generate_take(self, message=None, trigger_icd=False):
        # do not post if the channel hasn't been set or if the bot has been manually disabled
        if (self.channel_id == '') | (not self.enabled):
            return
        else:
            if trigger_icd:
                if message is None:
                    self.ready_for_random = False
                else:
                    self.ready_for_mention = False

            if message is None:
                if random.random() < 0.8 and (len(self.previous_messages)>5):
                    seed_text = random.choice([msg for msg in self.previous_messages[4:] if len(msg.split(' ')) > 5])
                    take_text = self.model.make_sentence(tries=50, message=seed_text)
                else:
                    take_text = self.model.make_sentence(tries=50)
                take_text = self.ensure_unique(format.text_cleaner(take_text))
            else:
                take_text = self.model.make_sentence(tries=50, message=message.content)

            self.log_take(take_text)

            take_text = format.add_suffix(format.text_cleaner(take_text))

            if message is not None:
                # sometimes add "because" to the beginning, if it's a "why" question
                if ('why' in message.content.split(' ')) & (random.random() < 0.8) :
                    pre = random.choice(['because', 'Because', 'bc'])
                    take_text = f'{pre} {take_text}'

                # sometimes answer yes/no questions
                yes_no_q = any([x in ['are', 'is', 'will', 'do', 'does', 'doesnt', 'am', 'should', 'have', 'would', 'did'] for x in message.content.split(' ')[:2]])
                if yes_no_q & (random.random() < 0.8):
                    pre = random.choice(['yea', 'ya', 'yeah', 'yep', 'na', 'nah', 'no', 'nope'])
                    punc = random.choice(['', '.', ','])
                    pre = f'{pre}{punc}'
                    take_text = f'{pre} {take_text}'

            return take_text

    def generate_rant(self, rant_size=None, trigger_icd=False):
        if rant_size is None:
            rant_size = self.rant_size

        # do not post if the channel hasn't been set or if the bot has been manually disabled
        if (self.channel_id == '') | (not self.enabled):
            return
        else:
            rant = ''

            for i in range(rant_size):
                sentence = self.ensure_unique(self.model.make_sentence())
                sentence = format.text_cleaner(sentence, remove_periods=False)
                sentence = format.add_period_if_needed(sentence)
                self.log_take(sentence)

                if len(rant + sentence) < 2000 - 30:
                    rant = f'{rant} {sentence}'
                else:
                    break

            if rant != '':
                rant = format.add_suffix(rant)

                if trigger_icd:
                    self.ready_for_random = False

                return rant
            else:
                pass

    def log_take(self, text):
        if len(self.previous_takes) >= self.max_previous_takes:
            self.previous_takes = self.previous_takes[1:]

        self.previous_takes.append(text)

    def ensure_unique(self, text, max_tries=20, reply_word=None):
        # do not re-use previous takes
        tries = 0
        while (text in self.previous_takes) & (tries < max_tries):
            if reply_word is None:
                text = self.model.make_sentence()
            else:
                text = self.model.make_sentence(message=reply_word)
            tries += 1

        return text

    def __str__(self):
        status = f'**Enabled**: {self.enabled}\n' \
                 f'**Learning**: {self.learn}\n' \
                 f'**Warlock-only**: {self.warlock_only}\n' \
                 f'**Sentences parsed**: {len(self.model.generator.parsed_sentences)}\n' \
                 f'**Chain**: {self.model.state_size}\n' \
                 f'**Data set**: {self.current_data_set}\n' \
                 f'**Mention reply cooldown**: {self.get_remaining_cooldown(kind="mention", string=True)} of {math.floor(self.mention_wait)}m\n' \
                 f'**Random take cooldown**: {self.get_remaining_cooldown(kind="random", string=True)} of {math.floor(self.random_wait)}m\n' \
                 f'**Rant chance**: {self.rant_chance}%\n' \
                 f'**Rant size**: {self.rant_size}\n'

        return status

    def train_full(self, train_dir=None, file=None):
        if train_dir is None:
            full_train_dir = self.training_root_dir
        else:
            full_train_dir = f'{self.training_root_dir}/{train_dir}'

        if not os.path.isdir(full_train_dir):
            raise FileNotFoundError

        if full_train_dir == f'{self.training_root_dir}/prophet':
            state_size = 3
        else:
            state_size = 2

        self.reset(state_size=state_size)

        training_files = [f for f in os.listdir(full_train_dir) if f.endswith('.txt')]

        for f in training_files:
            training_file_path = f'{full_train_dir}/{f}'

            lines = []

            if (file is None) or (f == file):
                with open(training_file_path, 'r', encoding='cp437') as f_data:
                    try:
                        for line in f_data:

                            if line.strip():
                                clean_line = format.text_cleaner(line)

                                if clean_line != '':
                                    lines.append(clean_line)
                    except:
                        pass

                self.model.update_model(lines)

        # in trained mode, disable further learning and ascension
        self.learn = False
        if train_dir != self.training_root_dir:
            self.current_data_set = train_dir

    def reset(self, state_size=2):
        self.current_data_set = 'none'
        self.learn = True

        self.can_generate_unique_takes = False

        self.model = model.Model(state_size=state_size)

    # adds message to markov model and sets flags for ready to post randomly or reply
    # to mention by checking the time elapsed since the last mention response or random post
    async def train(self, message):
        # incorporate the message into the model if learning is enabled and the message is long enough to learn from
        if self.learn & (len(message.content.split()) > self.model.generator.state_size):
            self.model.update_model(message.content)

        # set readiness flags
        self.can_generate_unique_takes = self.test_take_readiness()

        enough_time_elapsed = (time.time() - self.time_of_mention) >= self.mention_wait * 60
        if enough_time_elapsed & self.can_generate_unique_takes:
            self.ready_for_mention = True

        # have some additional anti-spam checks for random posting
        enough_messages_since_last_take = self.msgs_waited >= self.msgs_wait
        enough_time_elapsed = (time.time() - self.time_of_random) >= self.random_wait * 60
        if all((enough_time_elapsed, self.can_generate_unique_takes, enough_messages_since_last_take)):
            self.ready_for_random = True

    # if the model can spit out test_size unique takes, its model is "ready". once readiness is determined, do not check
    # again unless reset
    def test_take_readiness(self, test_size=15):
        if not self.can_generate_unique_takes:
            takes = [self.model.make_sentence() for x in range(test_size)]
            all_takes_unique = len(takes) == len(set(takes))

            return all_takes_unique
        else:
            return True

    def get_remaining_cooldown(self, kind, string=False):
        if kind == 'random':
            sec_remaining = max(0, (self.time_of_random + self.random_wait*60) - time.time())
        elif kind == 'mention':
            sec_remaining = max(0, (self.time_of_mention + self.mention_wait*60) - time.time())
        else:
            return

        ret = math.floor(sec_remaining)

        if not string: # return numeric value in seconds
            return ret
        else: # return string of minutes and seconds
            return format.time_to_text(sec_remaining)