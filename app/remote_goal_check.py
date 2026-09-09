import copy, tempfile
from pathlib import Path
import shared_state as s
import telegram_bot as b
seed=copy.deepcopy(s.DEFAULT_STATE)
seed['goals']=[{'id':'goal-1','name':'Viagem','target':1000.0,'saved':300.0,'tx':[]}]
with tempfile.TemporaryDirectory(prefix='weedtest-') as d:
    state_file=Path(d)/'state.json'
    with s.using_state_file(state_file, seed_state=seed):
        for text in ['saldo objetivo','objetivo','meta']:
            print('---', text)
            print(b.route_message({'chat':{'id':7121051643},'text':text})[1])
