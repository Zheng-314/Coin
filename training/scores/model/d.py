import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体支持
# plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def visualize_accuracy(csv_file):
    """读取CSV文件并可视化每个类别的准确率"""
    # 读取CSV文件
    df = pd.read_csv(csv_file, header=None)
    
    # 提取类别ID行和各轮准确率数据
    categories = df.iloc[0].tolist()
    accuracy_data = df.iloc[1:].reset_index(drop=True)
    
    # 设置轮数（根据数据行数确定）
    rounds = [f'{i+1}' for i in range(len(accuracy_data))]
    
    # 创建DataFrame，列名为类别ID，行索引为轮数
    accuracy_df = pd.DataFrame(columns=categories, index=rounds)
    
    # 填充数据
    for i in range(len(accuracy_data)):
        for j, cat in enumerate(categories):
            accuracy_df.loc[rounds[i], cat] = accuracy_data.iloc[i, j]
    
    # 转换数据类型为数值型
    accuracy_df = accuracy_df.apply(pd.to_numeric)
    
    # 创建图表
    plt.figure(figsize=(14, 8))
    
    # 绘制每个类别的准确率变化趋势
    # markers = ['o', 's', '^', 'D', 'v', 'p', '*', 'h', 'H', '8']
    markers = ['o', 's', '^', 'D', 'v', 'p', '*', 'h', 'H', '8', 
               'x', 'd', '|', '_', '+', '>', '<', '1', '2', '3', '4']
    for i, cat in enumerate(categories):  # 只显示前10个类别，避免图表过于拥挤
        plt.plot(rounds, accuracy_df[cat], marker=markers[i % len(markers)], 
                 linestyle='-', linewidth=2, label=f'class {cat}')
    
    # 添加图表标题和标签
    plt.title('val acc per class', fontsize=16)
    plt.xlabel('epoch', fontsize=14)
    plt.ylabel('acc (%)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='best', fontsize=10)
    plt.xticks(rotation=45)
    
    # # 添加平均值线
    # mean_accuracy = accuracy_df.mean(axis=1)
    # plt.plot(rounds, mean_accuracy, 'k--', linewidth=2, label='平均准确率')
    
    # # 显示具体数值
    # for i, round_data in enumerate(accuracy_df.values):
    #     for j, acc in enumerate(round_data):
    #         if j < 10:  # 只显示前10个类别
    #             plt.annotate(f'{acc:.1f}', 
    #                          (i, acc), 
    #                          textcoords="offset points", 
    #                          xytext=(0,5), 
    #                          ha='center',
    #                          fontsize=8)
    
    plt.tight_layout()
    plt.savefig('val_accuracy_trend.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 打印统计信息
    print("\n各类别最终准确率:")
    for cat in categories:
        print(f"类别 {cat}: {accuracy_df[cat].iloc[-1]:.2f}%")
    
    # print("\n平均准确率趋势:")
    # for r, acc in zip(rounds, mean_accuracy):
    #     print(f"{r}: {acc:.2f}%")

if __name__ == "__main__":
    csv_file = 'val_class_accuracies.csv'  # 替换为您的CSV文件路径
    visualize_accuracy(csv_file)