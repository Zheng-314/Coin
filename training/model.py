import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
from torchvision.models import VGG19_Weights

# SE模块
class SEBlock(nn.Module):
    def __init__(self, channel, reduction = 16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channel, channel // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channel // reduction, channel, bias=False),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        b,c,_,_ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1, 1)
        return x * y.expand_as(x)

# 预训练VGG19 with SE module
class VGG19(nn.Module):
    def __init__(self, num_classes=2, pretrained=True, se_positions=None):
        super(VGG19, self).__init__()
        
        # 加载预训练的VGG19模型，使用新的weights参数
        weights = VGG19_Weights.IMAGENET1K_V1 if pretrained else None
        vgg19 = models.vgg19(weights=weights)
        
        # 若未指定SE模块位置，默认在每个maxpooling后添加
        if se_positions is None:
            # 预训练VGG19中每个maxpooling层的索引
            maxpool_indices = [4, 9, 18, 27, 36]
            # 调整为在每个maxpooling后添加SE
            se_positions = [i + 1 for i in maxpool_indices]
        
        # 改造特征提取部分，插入SE模块
        features = list(vgg19.features)
        
        # 记录插入位置的偏移量
        offset = 0
        
        for pos in sorted(se_positions):
            # 找到前一个卷积层以获取通道数
            conv_idx = pos - 1 - offset
            while not isinstance(features[conv_idx], nn.Conv2d):
                conv_idx -= 1
            
            # 获取通道数并插入SE模块
            channel = features[conv_idx].out_channels
            features.insert(pos + offset, SEBlock(channel))
            offset += 1  # 更新偏移量
        
        self.features = nn.Sequential(*features)
        
        # 保持分类器不变，但修改最后一层以匹配类别数
        self.classifier = nn.Sequential(
            nn.Linear(512 * 7 * 7 * 2, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(128, num_classes)
        )

    def forward(self, x1, x2):
        front = self.features(x1)
        back = self.features(x2)
        x = torch.cat((front, back), dim = 1)
        x = x.view(x.size(0), -1)
        output = self.classifier(x)
        return output

    # def forward(self, input1, input2):
    #     output1 = self.forward_once(input1)
    #     output2 = self.forward_once(input2)
    #     return output1, output2

# 定义对比损失函数
class ContrastiveLoss(nn.Module):
    def __init__(self, margin=1.0):
        super(ContrastiveLoss, self).__init__()
        self.margin = margin

    def forward(self, output1, output2, label):
        euclidean_distance = nn.functional.pairwise_distance(output1, output2)
        loss_contrastive = torch.mean(label * torch.pow(euclidean_distance, 2) +
                                      (1-label)* torch.pow(torch.clamp(self.margin - euclidean_distance, min=0.0), 2))
        return loss_contrastive

if __name__ == '__main__':
    # 使用示例
    model = VGG19(num_classes=2)
    x1 = torch.randint(0,10, (2,3,224,224), dtype=torch.float32)
    x2 = torch.randint(0,10, (2,3,224,224),dtype=torch.float32)

    print(model(x1, x2))
    print(model)