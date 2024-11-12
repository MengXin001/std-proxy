# USENIX Security 2023 AE
## 中国的防火长城是如何检测和封锁完全加密流量的
本仓库是对[gfw-report/usenixsecurity23-artifact](https://github.com/gfw-report/usenixsecurity23-artifact)的Python实现，以拥有更良好的拓展性学习不同代理协议的流量特征，探索GFW黑箱。

本仓库中可见的一些`iptables`规则直接来源于原仓库，未作修改。除特殊说明外，相关func的args和原代码的作用一致，亦可直接参考原仓库的`README.md`配置args使用。

## 仓库结构和内容

## 注意事项
> 自2023年3月15日以来，GFW已停止动态流量拦截，因此你可能无法复现论文里的某些实验结果。