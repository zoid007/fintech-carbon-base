import sys
import json
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from backtestEngine import Strategy, Engine
import _lib

strategy_dandd = []


def read_json_file(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)


def write_json_file(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f)


def compare_operations(a, b, operation, data, idx):
    try:
        val_a = data.loc[idx, a]
        val_b = data.loc[idx, b]
    except KeyError as e:
        print(f"KeyError: {e}")
        print("Columns in data:")
        print(data.columns)
        print(f"a = {a}")
        print(f"b = {b}")
        return False
    
    operations = {
        'gt': val_a > val_b,
        'lt': val_a < val_b,
        'gte': val_a >= val_b,
        'lte': val_a <= val_b,
        'eq': val_a == val_b,
        'ne': val_a != val_b,
        'ca': _lib.crossover(data, a, b, idx),
        'cb': _lib.crossbelow(data, a, b, idx),
    }
    return operations.get(operation, False)


class SMACrossover(Strategy):
    def on_bar(self):
        if self.current_idx != 0:
            for index, i in enumerate(strategy_dandd):
                if 'SubFilter' in i:
                    if compare_operations(i['A'], i['B'], i['Operation'], self.data, self.current_idx) and compare_operations(i['subFilter']['A'], i['B'], i['subFilter']['Operation'], self.data, self.current_idx):
                        self.process_strategy(i)
                else:
                    if compare_operations(i['A'], i['B'], i['Operation'], self.data, self.current_idx):
                        self.process_strategy(i)

    def process_strategy(self, strategy):
        if self.position_size == 0:
            if strategy['Action'] == 'Long_Entry':
                order_size = self.cash / self.close
                self.buy_limit('AAPL', size=order_size, limit_price=self.close)
        elif strategy['Action'] == 'Long_Exit':
            if compare_operations(strategy['A'], strategy['B'], strategy['Operation'], self.data, self.current_idx):
                self.sell_limit('AAPL', size=self.position_size, limit_price=self.close)


def create_indicator(data, indicator, attr, close, variables):
    return getattr(ta, attr)(data[close], int(variables))


def main():
    input_file_path = sys.argv[1]
    output_file_path = sys.argv[2]

    input_data = read_json_file(input_file_path)
    jsondata = input_data
    data = yf.Ticker('AAPL').history(start='2012-12-01', end='2022-12-31', interval='1d')
    e = Engine(initial_cash=100000)

    process_json_data(data, jsondata)
    e.add_data(data)
    e.add_strategy(SMACrossover())
    stats = e.run()
    print(e.portfolio_bh)
    result_data = prepare_result_data(stats)
    write_json_file(output_file_path, {"result": result_data})


def process_json_data(data, jsondata):

    lastFilterIndex = 0

    for indx, i in enumerate(jsondata):

        strategy = {}
        subStrategy = {}
        
        if (i['type'] == 'filter'):
            lastFilterIndex = indx
            strategy['Operation'] = i['Operation']
            strategy['Action'] = i['Action']
            if (i['Operand']['OperandType'] == 'indicator'):
                indicator = i['Operand']['Indicators']['Attribute']+"_INDX"+str(indx)+str(i['Operand']['Indicators']['Variables'][0])+i['Operand']['Indicators']['Timeframe']
                data[indicator] = getattr(ta, i['Operand']['Indicators']['Attribute'])(data['Close'], int(i['Operand']['Indicators']['Variables'][0]))
                strategy['A'] = indicator
            if (i['OperandB']['OperandType'] == 'indicator'):
                indicator = i['OperandB']['Indicators']['Attribute']+"_INDX"+str(indx)+str(i['OperandB']['Indicators']['Variables'][0])+i['OperandB']['Indicators']['Timeframe']
                # data = resample(data, i['OperandB']['Indicators']['Timeframe'], indicator, i['Operand']['Indicators']['Attribute'], 'Close', int(i['Operand']['Indicators']['Variables'][0]))
                data[indicator] = getattr(ta, i['OperandB']['Indicators']['Attribute'])(data['Close'], int(i['OperandB']['Indicators']['Variables'][0]))
                print(i['OperandB']['Indicators']['Attribute']+"_INDX"+str(indx)+str(i['OperandB']['Indicators']['Variables'][0])+i['OperandB']['Indicators']['Timeframe'])
                strategy['B'] = indicator

            if (i['Operand']['OperandType'] == 'StockAttribute'):
                indicator = (i['Operand']['StockAttribute']['Indicators'])
                print(indicator)
                strategy['A'] = indicator

            if (i['OperandB']['OperandType'] == 'StockAttribute'):
                indicator = (i['OperandB']['StockAttribute']['Indicators'])
                print(indicator)
                strategy['B'] = indicator


            if (i['Operand']['OperandType'] == 'Constant'):
                indicator = (str(i['Operand']['Constant'])+"_INDX"+str(indx))
                strategy['A'] = indicator
                data[indicator] = i['Operand']['Constant']

            if (i['OperandB']['OperandType'] == 'Constant'):
                indicator = (str(i['OperandB']['Constant'])+"_INDX"+str(indx))
                strategy['B'] = indicator
                data[indicator] = i['OperandB']['Constant']
            strategy_dandd.append(strategy)


        elif (i['type'] == 'sub-filter'):
            
            for jindx, j in enumerate(jsondata):
                        
                subStrategy['Operation'] = j['Operation']

                if (j['Operand']['OperandType'] == 'indicator'):
                    indicator = j['Operand']['Indicators']['Attribute']+"_INDX"+str(jindx)+str(j['Operand']['Indicators']['Variables'][0])+j['Operand']['Indicators']['Timeframe']
                    data[indicator] = getattr(ta, j['Operand']['Indicators']['Attribute'])(data['Close'], int(j['Operand']['Indicators']['Variables'][0]))
                    subStrategy['A'] = indicator
                if (j['OperandB']['OperandType'] == 'indicator'):
                    indicator = j['OperandB']['Indicators']['Attribute']+"_INDX"+str(jindx)+str(j['OperandB']['Indicators']['Variables'][0])+j['OperandB']['Indicators']['Timeframe']
                    # data = resample(data, i['OperandB']['Indicators']['Timeframe'], indicator, i['Operand']['Indicators']['Attribute'], 'Close', int(i['Operand']['Indicators']['Variables'][0]))
                    data[indicator] = getattr(ta, j['OperandB']['Indicators']['Attribute'])(data['Close'], int(i['OperandB']['Indicators']['Variables'][0]))
                    print(j['OperandB']['Indicators']['Attribute']+"_INDX"+str(jindx)+str(j['OperandB']['Indicators']['Variables'][0])+j['OperandB']['Indicators']['Timeframe'])
                    subStrategy['B'] = indicator

                if (j['Operand']['OperandType'] == 'StockAttribute'):
                    indicator = (j['Operand']['StockAttribute']['Indicators'])
                    print(indicator)
                    subStrategy['A'] = indicator

                if (j['OperandB']['OperandType'] == 'StockAttribute'):
                    indicator = (j['OperandB']['StockAttribute']['Indicators'])
                    print(indicator)
                    subStrategy['B'] = indicator


                if (i['Operand']['OperandType'] == 'Constant'):
                    indicator = (str(j['Operand']['Constant'])+"_INDX"+str(jindx))
                    subStrategy['A'] = indicator
                    data[indicator] = j['Operand']['Constant']

                if (i['OperandB']['OperandType'] == 'Constant'):
                    indicator = (str(j['OperandB']['Constant'])+"_INDX"+str(jindx))
                    subStrategy['B'] = indicator
                    data[indicator] = j['OperandB']['Constant'] 

                strategy_dandd[lastFilterIndex]['subFilter'] = subStrategy  

    return strategy

def prepare_result_data(stats):
    print(stats)

if __name__ == "__main__":
    main()
