import json
import pandas as pd

orderbook = '/home/RajanV/data/orderbook.json'
def read_json(path):
    with open(path, 'r') as f:
        data = json.load(f)
        # Handle different JSON structures
    if isinstance(data, list):
        df = pd.DataFrame(data)
    elif isinstance(data, dict):
        df = pd.DataFrame([data])  # Create a DataFrame from a single dictionary
    return df
ob = read_json(orderbook)
warping = '/home/RajanV/data/warping_production.json'
wp = read_json(warping)

lst = wp.columns.to_list()
lst.append('Party Quantity (Meters)')
lst.append('Factory Order (Meters)')
lst.pop(lst.index('timestamp'))
ob['Design No.'] = ob['Design No.'].astype(str)
ob['Order No.'] = ob['Order No.'].astype(str)
tst = wp.merge(ob,left_on=['order_no','design_no'],right_on=['Order No.','Design No.'],how='inner')
pd.set_option('display.max_columns', 50)
print(tst)