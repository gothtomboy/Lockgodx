import random

import markovify

import format


class Model:

    def __init__(self, state_size=2):
        self.root_dir = 'models/'
        self.state_size = state_size
        self.init_text = 'i am a bot'
        self.no_take_text = 'cum'
        self.smart_reply_chance = 80
        self.generator = markovify.Text(self.init_text, state_size=state_size, well_formed=False)

    def make_sentence(self, message=None, tries=30):
        sentence = self.generator.make_sentence(tries=tries)

        if (message is not None) & (random.random() < self.smart_reply_chance/100):
            content = message.split(' ')
            content = format.remove_boring_words(content)
            random.shuffle(content)

            for word in content:
                try:
                    sentence = self.generator.make_sentence_with_start(beginning=word, tries=tries, strict=False)
                    break
                except markovify.text.ParamError:
                    pass

        if sentence:
            return sentence
        else:
            return self.no_take_text

    def update_model(self, text):
        try:
            new_model = markovify.Text(text, state_size=self.generator.state_size, well_formed=False)
            combined_model = markovify.combine(models=[self.generator, new_model])
            self.generator = combined_model
        except:
            pass

    def save_model(self, model_name=None):
        if model_name is None:
            model_name = 'default'

        try:
            model_json = self.generator.to_json()
            with open(f'{self.root_dir}{model_name}.json', 'w', encoding='cp437') as outfile:
                outfile.write(model_json)
            return 1
        except:
            return None

    def load_model(self, model_name=None):
        if model_name is None:
            model_name = 'default'

        try:
            model_json = open(f'{self.root_dir}{model_name}.json').read()
            self.generator = markovify.Text.from_json(model_json)
            return 1
        except:
            return None