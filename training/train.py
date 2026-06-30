import os
import torch
import torch.nn as nn
from PIL import Image
from matplotlib import pyplot as plt
from torch.utils.data import Dataset, random_split
from torchvision import models
from torchvision.transforms import transforms
import pandas as pd
import numpy as np
from model import VGG19

class ModifiedVGG19(nn.Module):
    def __init__(self, num_classes=5):
        super(ModifiedVGG19, self).__init__()
        # 加载预训练的 VGG19 模型
        self.vgg19 = models.vgg19(pretrained=True)
        # 去掉顶层结构
        features = list(self.vgg19.features.children())
        self.vgg19.features = nn.Sequential(*features)
        self.backbone = self.vgg19.features
        # 添加全局平均池化层
        # self.vgg19.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        # self.avgpool = nn.AdaptiveAvgPool2d((1, 1))

        # 冻结卷积层
        for param in self.backbone.parameters():
            param.requires_grad = False

        # 定义新的全连接层结构
        num_features = 25088  # VGG19 最后一层卷积层的输出通道数
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(num_features*2, 512),  # 第一个全连接层
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),  # Dropout 层，防止过拟合
            nn.Linear(512, 128),  # 第二个全连接层
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),  # Dropout 层，防止过拟合
            nn.Linear(128, num_classes)  # 输出层
        )

    def forward(self, x1, x2):
        front = self.backbone(x1)
        # front = self.avgpool(front)
        back = self.backbone(x2)
        # back = self.avgpool(back)
        x = torch.cat((front, back), dim = 1)
        # print(x.size())
        x = self.classifier(x)
        return x

class mydata(Dataset):
    def __init__(self, root, img_root=None, transform=None):
        self.path = root
        self.img_root = img_root or os.path.join(os.path.dirname(__file__), "..", "data", "images")
        self.transform = transform
        self.data = []
        with open(self.path, 'r') as f:
            for line in f:
                img1, img2, label = line.strip().split(',')
                self.data.append((img1, img2, label))

    def __getitem__(self, index):
        img1, img2, label = self.data[index]
        image1 = Image.open(os.path.join(self.img_root, img1))
        image2 = Image.open(os.path.join(self.img_root, img2))
        if self.transform:
            image1 = self.transform(image1)
            image2 = self.transform(image2)
        # label = torch.tensor(int(self.label_dict[label]))
        label = torch.tensor(int(label))
        # print(f"标签{label}")
        return image1, image2, label

    def __len__(self):
        return len(self.data)

# 使用示例
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    transform = transforms.Compose([
        transforms.Resize((224, 224)),  # 调整大小为 224x224
        transforms.RandomRotation(degrees=15),  # 随机旋转±15度
        transforms.ToTensor(),  # 转换为张量（形状：3x224x224，数值范围 [0, 1]）
        transforms.Normalize(  # 标准化
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    # 加载数据集
    # dataset = mydata('data_label.csv', transform)
    # train_set, val_set = random_split(dataset, [int(0.8 * len(dataset)), len(dataset) - int(0.8 * len(dataset))])
    train_set = mydata('train.csv', transform)
    val_set = mydata('val.csv',transform)

    # 创建数据加载器
    train_loader = torch.utils.data.DataLoader(train_set, batch_size=64, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_set, batch_size=64, shuffle=False)

    # 创建模型
    num_class = 26
    model = VGG19(num_classes=num_class).to(device)
    # model = ModifiedVGG19(num_classes=num_class).to(device)
    # # 加载之前的模型继续训练，该模型已经达到85%左右的准确率
    # model_path = "/workspace/pj_train/vgg19/model_5_20_85%/best_model.pth"  # 替换为你的模型文件路径
    # model.load_state_dict(torch.load(model_path))

    # 创建损失函数
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)  # 平滑强度0.1（经验值）
    # 创建优化器
    # optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-5)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.001, momentum=0.9, weight_decay=1e-5)

    # 创建学习率调度器
    # scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=5)

    train_losses = []
    val_losses = []
    train_accuracies = []
    val_accuracies = []
    grad_norms = []
    no_improvement = 0      # 记录连续多少个 epoch 没有提升
    epochs = 80
    best_val_acc = 0.0
    train_class_accuracies = {i: [] for i in range(num_class)}  # 假设3个类别
    val_class_accuracies = {i: [] for i in range(num_class)}    # 假设3个类别


    # 添加数据存储结构
    epoch_data = {
        'epoch': [],
        'train_loss': [],
        'val_loss': [],
        'train_accuracy': [],
        'val_accuracy': []
    }
    # 为每个类别添加存储字段
    for class_id in range(num_class):
        epoch_data[f'train_class_{class_id}_acc'] = []
        epoch_data[f'val_class_{class_id}_acc'] = []

    try:
        for epoch in range(epochs):
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_class_correct = {i: 0 for i in range(num_class)}  # 假设3个类别
            train_class_total = {i: 0 for i in range(num_class)}    # 假设3个类别
            for i, (input1, input2, labels) in enumerate(train_loader):
                optimizer.zero_grad()
                input1 = input1.to(device)
                input2 = input2.to(device)
                labels = labels.to(device)
                outputs = model(input1, input2)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                train_correct += (predicted == labels).sum().item()
                # 计算每个类别的正确预测数和总样本数
                for label, pred in zip(labels, predicted):
                    train_class_correct[label.item()] += (label == pred).item()
                    train_class_total[label.item()] += 1
                # 计算梯度范数
                total_norm = 0
                for p in model.parameters():
                    if p.requires_grad and p.grad is not None:
                        param_norm = p.grad.data.norm(2)
                        total_norm += param_norm.item() ** 2
                total_norm = total_norm ** 0.5
                grad_norms.append(total_norm)

            # 计算每个类别的准确率
            for class_id in range(num_class):  # 假设3个类别
                if train_class_total[class_id] > 0:
                    accuracy = train_class_correct[class_id] / train_class_total[class_id] * 100
                else:
                    accuracy = 0.0
                train_class_accuracies[class_id].append(accuracy)

            train_losses.append(train_loss / len(train_loader))
            train_accuracy = (train_correct / len(train_set)) * 100
            train_accuracies.append(train_accuracy)
            if epoch % 10 == 0:
                torch.save(model.state_dict(), f'model/model_{epoch}.pth')

            model.eval()
            with torch.no_grad():
                val_loss = 0.0
                val_correct = 0
                val_class_correct = {i: 0 for i in range(num_class)}  # 假设3个类别
                val_class_total = {i: 0 for i in range(num_class)}    # 假设3个类别
                for i, (input1, input2, labels) in enumerate(val_loader):
                    input1 = input1.to(device)
                    input2 = input2.to(device)
                    labels = labels.to(device)

                    outputs = model(input1, input2)

                    loss = criterion(outputs, labels)
                    val_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    val_correct += (predicted == labels).sum().item()
                    # 计算每个类别的正确预测数和总样本数
                    for label, pred in zip(labels, predicted):
                        val_class_correct[label.item()] += (label == pred).item()
                        val_class_total[label.item()] += 1

                # 计算每个类别的准确率
                for class_id in range(num_class):  # 假设3个类别
                    if val_class_total[class_id] > 0:
                        accuracy = val_class_correct[class_id] / val_class_total[class_id] * 100
                    else:
                        accuracy = 0.0
                    val_class_accuracies[class_id].append(accuracy)

                val_losses.append(val_loss / len(val_loader))
                val_accuracy = (val_correct / len(val_set)) * 100
                val_accuracies.append(val_accuracy)

            # 训练 epoch 结束后收集数据
            epoch_data['epoch'].append(epoch + 1)
            epoch_data['train_loss'].append(train_losses[-1])
            epoch_data['val_loss'].append(val_losses[-1])
            epoch_data['train_accuracy'].append(train_accuracy)
            epoch_data['val_accuracy'].append(val_accuracy)
            
            # 收集每个类别的准确率
            for class_id in range(num_class):
                epoch_data[f'train_class_{class_id}_acc'].append(train_class_accuracies[class_id][-1])
                epoch_data[f'val_class_{class_id}_acc'].append(val_class_accuracies[class_id][-1])

            # 早停与模型保存
            if val_accuracy > best_val_acc:
                best_val_acc = val_accuracy
                no_improvement = 0
                torch.save(model.state_dict(), "model/best_model.pth")
            # else:
            #     no_improvement += 1
            #     if no_improvement >= 10:
            #         print('Early stopping')
            #         break
            #
            scheduler.step(val_loss)
            print(f'Epoch {epoch + 1}/{epochs}, Train Loss: {train_losses[-1]}, Train Acc: {train_accuracy}%, Val Loss: {val_losses[-1]}, Val Acc: {val_accuracy}%')

            # 转换为 DataFrame 并保存 CSV
            df = pd.DataFrame(epoch_data)
            df.to_csv('model/epoch_metrics.csv', index=False)

    except KeyboardInterrupt:
        print("程序被用户中断，正在保存损失图...")

    finally:
        # 保存每个类别的准确率到CSV文件
        train_class_df = pd.DataFrame(train_class_accuracies)
        train_class_df.to_csv('model/train_class_accuracies.csv', index=False)

        val_class_df = pd.DataFrame(val_class_accuracies)
        val_class_df.to_csv('model/val_class_accuracies.csv', index=False)

        plt.figure(figsize=(15, 5))
        plt.subplot(1, 3, 1)
        plt.plot(train_losses, label='Training Loss')
        plt.plot(val_losses, label='Validation Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.legend()

        plt.subplot(1, 3, 2)
        plt.plot(train_accuracies, label='Training Accuracy')
        plt.plot(val_accuracies, label='Validation Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.title('Training and Validation Accuracy')
        plt.legend()

        plt.subplot(1, 3, 3)
        plt.plot(grad_norms, label='Gradient Norm')
        plt.xlabel('Step')
        plt.ylabel('Gradient Norm')
        plt.title('Gradient Norm')
        plt.legend()

        plt.tight_layout()
        plt.savefig("model/loss.png")
        plt.show()

        # 绘制每个类别的准确率变化图表
        plt.figure(figsize=(15, 5))
        for class_id in range(num_class):  # 假设3个类别
            plt.subplot(1, 3, class_id + 1)
            plt.plot(train_class_accuracies[class_id], label=f'Train Class {class_id}')
            plt.plot(val_class_accuracies[class_id], label=f'Val Class {class_id}')
            plt.xlabel('Epoch')
            plt.ylabel('Accuracy')
            plt.title(f'Class {class_id} Accuracy')
            plt.legend()

        plt.tight_layout()
        plt.savefig("model/class_accuracies.png")
        plt.show()

        # 绘制所有类别的训练准确率曲线图
        plt.figure(figsize=(10, 6))
        for class_id in range(num_class):  # 假设3个类别
            plt.plot(train_class_accuracies[class_id], label=f'Train Class {class_id}')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.title('Training Accuracy for All Classes')
        plt.legend()
        plt.tight_layout()
        plt.savefig("model/all_train_class_accuracies.png")
        plt.show()

        # 绘制所有类别的验证准确率曲线图
        plt.figure(figsize=(10, 6))
        for class_id in range(num_class):  # 假设3个类别
            plt.plot(val_class_accuracies[class_id], label=f'Val Class {class_id}')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.title('Validation Accuracy for All Classes')
        plt.legend()
        plt.tight_layout()
        plt.savefig("model/all_val_class_accuracies.png")
        plt.show()