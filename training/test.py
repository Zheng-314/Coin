import torch
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
from torchvision import models
from PIL import Image
import matplotlib.pyplot as plt
from model import VGG19
import pandas as pd 
# 设置 matplotlib 支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定使用黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

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
    def __init__(self, root, transform=None):
        self.path = root
        self.transform = transform
        self.data = []
        with open(self.path, 'r') as f:
            for line in f:
                img1, img2, label = line.strip().split(',')
                self.data.append((img1, img2, label))
        # self.label_dict = {'45': 0,'50': 1,'53': 2,'55': 3,'58': 4,'61': 5,'63': 6}

    def __getitem__(self, index):
        img1, img2, label = self.data[index]
        image1 = Image.open("/workspace/vggse/photo/" + img1)
        image2 = Image.open("/workspace/vggse/photo/" + img2)
        if self.transform:
            image1 = self.transform(image1)
            image2 = self.transform(image2)
        # label = torch.tensor(int(self.label_dict[label]))
        label = torch.tensor(int(label))
        # print(f"标签{label}")
        return image1, image2, label

    def __len__(self):
        return len(self.data)

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

testset = mydata("/workspace/vggse/test.csv", transform=transform)

testloader = torch.utils.data.DataLoader(testset, batch_size = 32 , shuffle = False)
model = VGG19(3).to(device)
model.load_state_dict(torch.load("/workspace/vggse/model/best_model.pth"))

model.eval()


# 测试模型
class_correct = list(0. for _ in range(3))
class_total = list(0. for _ in range(3))

                
with torch.no_grad():
    for i, (input1, input2, labels) in enumerate(testloader):
        input1 = input1.to(device)
        input2 = input2.to(device)
        labels = labels.to(device)
        outputs = model(input1, input2)

        _, predicted = torch.max(outputs.data, 1)

        c = (predicted == labels).squeeze()
        for i in range(len(labels)):
            label = labels[i]
            class_correct[label] += c[i].item()
            class_total[label] += 1

# 计算每一类的准确率
class_accuracy = []
for i in range(3):
    if class_total[i] == 0:
        class_accuracy.append(0)
    else:
        class_accuracy.append(100 * class_correct[i] / class_total[i])

# 保存准确率到CSV文件
accuracy_data = {
    'Class': [0, 1, 2],
    'Accuracy(%)': class_accuracy
}

df = pd.DataFrame(accuracy_data)
df.to_csv('class_accuracy.csv', index=False)
print("每类准确率已保存到 class_accuracy.csv")
# 绘制柱状图
plt.figure(figsize=(10, 6))
bars = plt.bar([0,1,2], class_accuracy)
# 在每个柱子上面显示数值
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width() / 2., height + 1,
             f'{height:.2f}%', ha='center', va='bottom')
plt.xlabel('Classes')
plt.ylabel('Accuracy(%)')
plt.title('accuracy for every class', y=1.05)
plt.ylim(0, 100)
plt.savefig('test_accuracy.png')
plt.show()

