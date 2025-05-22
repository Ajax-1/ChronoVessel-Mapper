# 舰船纹理贴图算法集成指南

本文档详细介绍如何将Blender贴图算法集成到基于Vue3前端和Java后端的项目中。

## 1. 系统架构

![系统架构图](https://placeholder-for-architecture-diagram.com)

系统由三个主要部分组成:
- **前端**: Vue3应用，提供用户交互界面
- **后端**: Java Spring Boot应用，处理业务逻辑和数据管理
- **算法服务**: Blender脚本，由后端调用执行贴图处理

## 2. 前提条件

- Java JDK 11或更高版本
- Maven或Gradle构建工具
- Node.js 14或更高版本
- Blender 3.x或更高版本
- MySQL数据库

## 3. 开发环境搭建

### 3.1 安装Blender

1. 从[Blender官网](https://www.blender.org/download/)下载并安装Blender
2. 确认Blender可以从命令行启动:
   ```bash
   blender --version
   ```

### 3.2 配置后端环境

1. 创建MySQL数据库:
   ```sql
   CREATE DATABASE ship_texture_db;
   ```

2. 配置`application.properties`:
   ```properties
   # Blender路径 - 根据实际安装位置修改
   app.blender.path=/usr/bin/blender
   
   # 算法脚本路径 - 根据实际存放位置修改
   app.blender.script=/path/to/algorithm/bash_V2_end_520_副本.py
   
   # 其他配置保持默认或根据需要调整
   ```

### 3.3 配置前端环境

1. 创建`.env`文件:
   ```
   VITE_API_BASE_URL=http://localhost:8080
   ```

## 4. 集成步骤

### 4.1 安装算法脚本

1. 将修改后的`bash_V2_end_520_副本.py`脚本复制到指定目录:
   ```bash
   mkdir -p algorithm
   cp bash_V2_end_520_副本.py algorithm/
   ```

2. 确认脚本可以独立运行:
   ```bash
   blender --background --python algorithm/bash_V2_end_520_副本.py -- test_model.ply test_top_texture.jpg test_side_texture.jpg output.glb log.txt
   ```

### 4.2 准备数据模型和数据库

1. 创建必要的实体类:
   - `ShipModel`: 存储船型3D模型数据
   - `Texture`: 存储纹理图片数据

2. 创建数据表:
   ```sql
   CREATE TABLE ship_models (
     id BIGINT PRIMARY KEY AUTO_INCREMENT,
     name VARCHAR(255) NOT NULL,
     description TEXT,
     model_data LONGBLOB NOT NULL,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   
   CREATE TABLE textures (
     id BIGINT PRIMARY KEY AUTO_INCREMENT,
     date VARCHAR(100) NOT NULL,
     description TEXT,
     top_texture_data LONGBLOB NOT NULL,
     side_texture_data LONGBLOB NOT NULL,
     ship_model_id BIGINT,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     FOREIGN KEY (ship_model_id) REFERENCES ship_models(id)
   );
   ```

### 4.3 集成后端

1. 导入示例代码:
   - `TexturingService.java`: 处理贴图逻辑
   - `TexturingController.java`: 提供REST API

2. 创建所需的DTO类:
   - `ShipTypeDTO`
   - `TextureDateDTO`
   - `TexturingRequestDTO`
   - `TexturingResponseDTO`

3. 实现存储库接口:
   - `ShipModelRepository`
   - `TextureRepository`

### 4.4 集成前端

1. 安装所需依赖:
   ```bash
   npm install @google/model-viewer
   ```

2. 将`ShipTextureApp.vue`组件集成到Vue项目中

3. 在路由配置中添加组件:
   ```javascript
   const routes = [
     // 其他路由...
     {
       path: '/texturing',
       name: 'Texturing',
       component: () => import('@/views/ShipTextureApp.vue')
     }
   ]
   ```

## 5. 运行和测试

### 5.1 启动后端

```bash
cd backend
./mvnw spring-boot:run
```

### 5.2 启动前端

```bash
cd frontend
npm run dev
```

### 5.3 测试流程

1. 访问`http://localhost:3000/texturing`
2. 选择船型和纹理日期
3. 点击"生成贴图模型"按钮
4. 等待处理完成
5. 查看生成的3D模型

## 6. 生产环境部署

### 6.1 后端部署

1. 构建项目:
   ```bash
   ./mvnw clean package
   ```

2. 运行JAR文件:
   ```bash
   java -jar target/ship-texture-0.0.1-SNAPSHOT.jar
   ```

### 6.2 前端部署

1. 构建前端:
   ```bash
   npm run build
   ```

2. 将生成的`dist`目录部署到Web服务器

### 6.3 Blender安装

1. 在生产服务器上安装Blender
2. 确保服务器具有足够的GPU资源（如果有大量贴图处理需求）

## 7. 故障排除

### 7.1 常见问题

1. **Blender命令未找到**
   - 确认Blender已正确安装
   - 检查`app.blender.path`配置是否正确

2. **贴图处理失败**
   - 检查日志文件中的具体错误信息
   - 确认输入的模型和纹理格式正确

3. **请求超时**
   - 增加处理超时时间
   - 考虑使用异步处理和WebSocket通知

### 7.2 日志位置

- 后端日志: `logs/application.log`
- 算法日志: 每个处理任务的日志位于`temp/{jobId}/process.log`

## 8. 扩展和优化

### 8.1 支持更多模型和纹理格式

在Blender脚本中已添加支持多种模型格式:
- PLY
- OBJ
- FBX
- STL
- GLTF/GLB

### 8.2 任务队列和并行处理

对于高负载场景，可以实现任务队列:
- 使用Redis或RabbitMQ作为队列
- 实现处理工作器池
- 添加任务状态跟踪

### 8.3 结果缓存

对于相同参数的请求，可以缓存结果避免重复处理:
- 使用Redis存储处理结果索引
- 实现缓存失效策略 