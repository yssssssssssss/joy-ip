# Logger未定义错误修复

## 问题描述
```
分析用户需求失败: name 'logger' is not defined
```

## 问题原因
`content_agent_2d.py` 继承了 `ContentAgent` 类，当调用父类的 `_analyze_content_combined` 方法时，该方法中使用了模块级别的 `logger` 变量。但由于Python的作用域规则，子类模块中的logger变量无法被父类方法直接访问。

## 解决方案
将logger从模块级别改为类属性，或者确保所有使用logger的地方都能正确访问到logger实例。

### 方案1：使用self.logger（推荐）
在类中创建logger属性，所有方法通过self.logger访问。

### 方案2：确保模块级logger正确初始化
在每个使用logger的方法中，确保logger已经被正确导入和初始化。

## 实施方案
采用方案2，因为改动最小，只需要确保logger在使用前已经正确初始化。
