# 舰船纹理贴图系统

该系统基于Vue3前端和Java后端，调用Blender算法进行舰船3D模型纹理贴图处理。

## 系统架构

系统由三部分组成：
1. **前端**：使用Vue3开发的用户界面，提供船型选择、日期选择和渲染展示功能
2. **后端**：使用Java Spring Boot开发的服务器，处理数据管理和业务逻辑
3. **算法服务**：基于Blender的Python脚本，负责实际贴图处理

## 数据流程

1. 用户在前端界面选择船型和纹理日期
2. 前端发送请求到后端
3. 后端从数据库获取对应的3D模型和纹理图片
4. 后端调用Blender执行贴图算法
5. 算法处理完成后生成GLB格式的3D模型
6. 后端将结果URL返回给前端
7. 前端加载并展示处理后的3D模型

## 部署要求

1. **前端**：Node.js环境
2. **后端**：Java环境，Maven/Gradle构建工具
3. **算法服务**：Blender 3.x或更高版本

## 目录结构

```
project/
├── frontend/          # Vue3前端项目
├── backend/           # Java后端项目
└── algorithm/         # Blender贴图算法脚本
```

## 使用方法

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 后端开发

```bash
cd backend
./mvnw spring-boot:run
```

### 算法脚本调用

```bash
blender --background --python algorithm/bash_V2_end_520.py -- 模型文件 顶部纹理文件 侧面纹理文件 输出文件路径 [日志文件路径]
``` 