import pandas as pd
from sklearn.model_selection import train_test_split
data = pd.read_csv('tdata.csv')

# 图像路径和标签
path = data.iloc[:,0:2]
label = data.iloc[:,3]
print(path.head)
print(label.head)
# 
x_train, x_temp, y_train, y_temp = train_test_split(path, label, test_size=0.3,
            stratify = label, random_state=42)

x_test, x_val, y_test, y_val = train_test_split(x_temp, y_temp, test_size=1/3,
            stratify = y_temp, random_state=42)

train_data = pd.DataFrame({
    'path1': x_train.iloc[:, 0],
    'path2': x_train.iloc[:, 1],
    'score': y_train
})

test_data = pd.DataFrame({
    'path1': x_test.iloc[:, 0],
    'path2': x_test.iloc[:, 1],
    'score': y_test
})

val_data = pd.DataFrame({
    'path1': x_val.iloc[:, 0],
    'path2': x_val.iloc[:, 1],
    'score': y_val
})

train_data.to_csv('train.csv', index = False)
test_data.to_csv('test.csv', index = False)
val_data.to_csv('val.csv', index = False)
print(path)
print(label)

