from src.selectors.strategies.base import StrategyFactory; strategies = [{'type': 'text_anchor', 'anchor_text': 'test'}, {'type': 'css', 'selector': '.test'}, {'type': 'xpath', 'selector': '//div'}]; [print(f'✅ {c[\
type\]}: {StrategyFactory.create_strategy(c).type}') for c in strategies]; print('All strategies work!')
