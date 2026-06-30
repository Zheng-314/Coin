import pandas as pd
import matplotlib.pyplot as plt

# 读取 CSV 文件
df = pd.read_csv('epoch_metrics.csv')

# 获取 epoch 列
epochs = df['epoch'].values

# 获取类别列的名称
category_columns = [col for col in df.columns if col.startswith('train_class') or col.startswith('val_class')]

# 提取唯一的类别编号
unique_class_nums = list(set([col.split('_')[-2] for col in category_columns if 'acc' in col]))

# 创建一个图和两个子图
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 15))

# 绘制训练准确率
for class_num in unique_class_nums:
    train_col = f'train_class_{class_num}_acc'
    if train_col in df.columns:
        ax1.plot(epochs, df[train_col], label=f'Train Class {class_num}')

ax1.set_title('Training Accuracy per Class')
ax1.set_xlabel('Epoch')
ax1.set_ylabel('Accuracy (%)')
ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
ax1.grid(True)

# 绘制验证准确率
for class_num in unique_class_nums:
    val_col = f'val_class_{class_num}_acc'
    if val_col in df.columns:
        ax2.plot(epochs, df[val_col], label=f'Val Class {class_num}')

ax2.set_title('Validation Accuracy per Class')
ax2.set_xlabel('Epoch')
ax2.set_ylabel('Accuracy (%)')
ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
ax2.grid(True)

# 调整布局
plt.tight_layout()

# 保存图表
plt.savefig("accuracy.png")

# 显示图表
plt.show()


