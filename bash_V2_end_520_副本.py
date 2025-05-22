import bpy
import os
import sys
import math
import bmesh
import json
import traceback
from mathutils import Vector, Matrix
import logging

# 设置日志记录
log_file = None
try:
    # 从命令行获取参数
    # 格式：blender --background --python script.py -- model_file texture_top texture_side output_file [log_file]
    # 注意：需要跳过blender自己的参数，所以我们查找"--"之后的参数
    args = sys.argv
    
    # 尝试查找'--'参数
    try:
        arg_index = args.index("--") + 1
    except ValueError:
        print("错误: 未找到参数分隔符'--'")
        print("使用方法: blender --background --python script.py -- model_file texture_top texture_side output_file [log_file]")
        sys.exit(1)
    
    # 检查参数数量
    if len(args) < arg_index + 4:
        print("错误: 参数不足")
        print("使用方法: blender --background --python script.py -- model_file texture_top texture_side output_file [log_file]")
        sys.exit(1)
    
    # 获取参数
    model_path = args[arg_index]
    texture_top_path = args[arg_index + 1]
    texture_side_path = args[arg_index + 2]
    output_path = args[arg_index + 3]
    
    # 可选: 日志文件路径
    if len(args) > arg_index + 4:
        log_file = args[arg_index + 4]
    
    # 设置日志记录
    if log_file:
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] %(message)s'
        )
    
    logger = logging.getLogger(__name__)
    logger.info("开始执行贴图脚本...")
    
    # 检查输入文件是否存在
    for file_path, file_desc in [
        (model_path, "模型文件"),
        (texture_top_path, "顶部纹理"),
        (texture_side_path, "侧面纹理")
    ]:
        if not os.path.exists(file_path):
            logger.error(f"{file_desc}不存在: {file_path}")
            sys.exit(1)
    
    # 创建输出目录
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"已创建输出目录: {output_dir}")
    
    # === 初始化函数定义 ===
    def project_from_view_manual(obj, camera):
        """基于透视相机进行精确UV投影"""
        logger.info(f"基于透视相机 {camera.name} 参数计算UV投影")
    
        # 确保在编辑模式
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
    
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
    
        # 获取UV层
        uv_layer = bm.loops.layers.uv.verify()
    
        # 获取相机参数
        cam_data = camera.data
        is_persp = cam_data.type == 'PERSP'  # 确认是透视相机
    
        # 获取相机到世界的转换矩阵及其逆矩阵
        cam_matrix_world = camera.matrix_world
        cam_matrix_world_inv = cam_matrix_world.inverted()
    
        # 获取选中的面
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            logger.warning("没有选中的面，无法进行UV投影")
            return
    
        # 输出调试信息
        logger.info(f"相机类型: {'透视' if is_persp else '正交'}")
        logger.info(f"相机位置: {cam_matrix_world.translation}")
    
        # 为透视相机获取视野和宽高比
        if is_persp:
            sensor_width = cam_data.sensor_width
            sensor_height = cam_data.sensor_height
            focal_length = cam_data.lens
    
            # 计算视野 (FOV)
            fov = 2 * math.atan(sensor_width / (2 * focal_length))
            aspect_ratio = sensor_width / sensor_height
    
            logger.info(f"焦距: {focal_length}mm, 视野: {math.degrees(fov):.1f}°, 宽高比: {aspect_ratio:.2f}")
    
        # 应用UV坐标
        for face in selected_faces:
            for loop in face.loops:
                # 获取顶点的全局坐标
                vert_global = obj.matrix_world @ loop.vert.co
    
                # 将顶点转换到相机空间
                vert_view = cam_matrix_world_inv @ vert_global
    
                # 针对透视相机的UV计算
                if is_persp:
                    # 透视投影 - 与Blender内部算法更接近
                    # z轴指向相机后方，所以需要用-z
                    if vert_view.z < 0:  # 确保在相机前方（z为负值表示在相机前方）
                        # 透视除法
                        screen_x = vert_view.x / -vert_view.z
                        screen_y = vert_view.y / -vert_view.z
    
                        # 根据视野和宽高比调整
                        fov_factor = math.tan(fov / 2)
                        u = 0.5 + screen_x / (2 * fov_factor * aspect_ratio)
                        v = 0.5 + screen_y / (2 * fov_factor)
                    else:
                        # 如果顶点在相机后面，设置默认值
                        u, v = 0.5, 0.5
                else:
                    # 正交投影（以防相机类型不是透视）
                    u = 0.5 + vert_view.x / 10.0
                    v = 0.5 + vert_view.y / 10.0
    
                # 设置UV坐标
                loop[uv_layer].uv = (u, v)
    
        # 更新网格
        bmesh.update_edit_mesh(mesh)
        logger.info("UV投影计算完成")
    
    
    def setup_material_with_texture(obj, material_index, texture_path):
        """设置材质并应用纹理"""
        try:
            # 获取材质
            mat = obj.material_slots[material_index].material
            
            # 设置材质节点
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            nodes.clear()  # 清除默认节点
            
            # 创建着色器节点
            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            bsdf.location = (300, 0)
            
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (500, 0)
            
            # 连接主着色器到输出
            mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
            
            # 加载纹理
            img = bpy.data.images.load(filepath=texture_path)
            
            # 创建图像纹理节点
            tex_img = nodes.new(type='ShaderNodeTexImage')
            tex_img.location = (0, 0)
            tex_img.image = img
            
            # 连接纹理到着色器
            mat.node_tree.links.new(tex_img.outputs['Color'], bsdf.inputs['Base Color'])
            
            logger.info(f"已应用纹理 {texture_path} 到材质 {mat.name}")
            return mat
        except Exception as e:
            logger.error(f"应用纹理失败: {str(e)}")
            return None
    
    
    # === 主脚本开始 ===
    try:
        logger.info("开始执行贴图流程...")
        
        # 清除Blender中的默认对象
        logger.info("正在清除默认对象...")
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        # 导入模型文件
        extension = os.path.splitext(model_path)[1].lower()
        
        logger.info(f"正在导入模型文件: {model_path} (类型: {extension})")
        
        if extension == ".ply":
            bpy.ops.wm.ply_import(filepath=model_path, files=[{"name": os.path.basename(model_path)}])
        elif extension == ".obj":
            bpy.ops.wm.obj_import(filepath=model_path, files=[{"name": os.path.basename(model_path)}])
        elif extension == ".fbx":
            bpy.ops.import_scene.fbx(filepath=model_path)
        elif extension == ".stl":
            bpy.ops.import_mesh.stl(filepath=model_path)
        elif extension == ".glb" or extension == ".gltf":
            bpy.ops.import_scene.gltf(filepath=model_path)
        else:
            logger.error(f"不支持的模型文件格式: {extension}")
            sys.exit(1)
        
        # 定义相机配置列表
        camera_configs = [
            {
                "name": "Camera_Top",
                "location": (0, 0, 16),
                "rotation": (0, 0, math.pi / 2),
                "material_name": "Material_Top",
                "texture_path": texture_top_path,  # 顶部纹理
                "model_rotation": (0, 0, 0),  # 模型处理时的旋转角度
                "selection_params": {
                    "axis": 2,  # Z轴
                    "find_max": True,  # 查找最大值
                    "epsilon": 1.5,
                    "normal_direction": (0, 0, 1)  # 法线指向Z轴正方向
                }
            },
            {
                "name": "Camera_Side",
                "location": (14, 0, 1.3),
                "rotation": (math.pi / 2, 0, math.pi / 2),
                "material_name": "Material_Side",
                "texture_path": texture_side_path,  # 侧面纹理
                "model_rotation": (0, math.pi / 2, 0),  # 示例：绕Y轴旋转90度
                "selection_params": {
                    "axis": 0,  # X轴
                    "find_max": True,  # 查找最大值
                    "epsilon": 1.5,
                    "normal_direction": (1, 0, 0)  # 法线指向X轴正方向
                }
            }
        ]
        
        # 寻找网格对象
        mesh_obj = None
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                mesh_obj = obj
                # 初始化时先保存原始变换
                original_location = mesh_obj.location.copy()
                original_rotation = mesh_obj.rotation_euler.copy()
                original_scale = mesh_obj.scale.copy()
                logger.info(f"已保存模型 {mesh_obj.name} 的原始变换属性")
                break
        
        if not mesh_obj:
            logger.error("场景中没有找到网格对象")
            sys.exit(1)
        
        # 确保有足够的材质槽
        while len(mesh_obj.material_slots) < len(camera_configs):
            bpy.context.view_layer.objects.active = mesh_obj
            bpy.ops.object.material_slot_add()
        
        # 创建材质
        for i, config in enumerate(camera_configs):
            mat = bpy.data.materials.new(name=config["material_name"])
            mesh_obj.material_slots[i].material = mat
            mat.use_nodes = True
            logger.info(f"已创建材质: {config['material_name']}")
        
        # === 预先创建所有相机 ===
        cameras = []
        logger.info("开始预先创建所有相机...")
        
        # 确保处于对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        
        # 创建所有相机
        for i, config in enumerate(camera_configs):
            bpy.ops.object.camera_add(
                enter_editmode=False,
                align='WORLD',
                location=config["location"],
                rotation=config["rotation"]
            )
            camera = bpy.context.active_object
            camera.name = config["name"]
            cameras.append(camera)
            logger.info(f"已创建相机: {config['name']}")
        
            # 取消选择，避免上下文污染
            bpy.ops.object.select_all(action='DESELECT')
        
        # === 处理每个相机视角和对应的面 ===
        for i, config in enumerate(camera_configs):
            camera = cameras[i]
            logger.info(f"开始处理相机配置 {i + 1}/{len(camera_configs)}: {config['name']}")
        
            # 设置活动相机
            bpy.context.scene.camera = camera
        
            # 旋转模型到指定角度
            bpy.ops.object.select_all(action='DESELECT')
            mesh_obj.select_set(True)
            bpy.context.view_layer.objects.active = mesh_obj
            bpy.ops.object.mode_set(mode='OBJECT')
        
            # 调整模型旋转以匹配相机视角
            mesh_obj.rotation_euler = config["model_rotation"]
            logger.info(f"已将模型旋转到相机 {config['name']} 对应的角度")
        
            # 进入编辑模式选择面
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(mesh_obj.data)
            matrix_world = mesh_obj.matrix_world
        
            # 取消所有面的选择
            for face in bm.faces:
                face.select = False
        
            # 提取选择参数
            sp = config["selection_params"]
            axis = sp["axis"]
            find_max = sp["find_max"]
            epsilon = sp["epsilon"]
            normal_dir = sp["normal_direction"]
        
            # 计算极值坐标（找出最高点或最远点）
            if find_max:
                extreme_coord = max((matrix_world @ v.co)[axis] for v in bm.verts)
            else:
                extreme_coord = min((matrix_world @ v.co)[axis] for v in bm.verts)
        
            # 选择满足条件的面（位置和法线方向）
            selected_faces_count = 0
            for face in bm.faces:
                # 获取面的世界坐标和法线
                verts_world_coords = [(matrix_world @ v.co)[axis] for v in face.verts]
                normal_world = matrix_world.to_3x3() @ face.normal
        
                # 检查面的位置条件
                coord_condition = False
                if find_max:
                    coord_condition = all(c >= extreme_coord - epsilon for c in verts_world_coords)
                else:
                    coord_condition = all(c <= extreme_coord + epsilon for c in verts_world_coords)
        
                # 检查面的法线方向条件
                normal_condition = normal_world[axis] * normal_dir[axis] > 0
        
                # 如果同时满足位置和法线条件，选中此面
                if coord_condition and normal_condition:
                    face.select = True
                    selected_faces_count += 1
        
            logger.info(f"已为相机 {config['name']} 选择了 {selected_faces_count} 个面")
            bmesh.update_edit_mesh(mesh_obj.data)
        
            # 设置活动材质并分配给选中面
            mesh_obj.active_material_index = i
            bpy.ops.object.material_slot_assign()
        
            # 执行基于相机的UV投影
            project_from_view_manual(mesh_obj, camera)
        
            # 设置材质和纹理
            setup_material_with_texture(mesh_obj, i, config["texture_path"])
        
            # 如果不是最后一个相机，恢复模型原始旋转角度以处理下一个视角
            if i < len(camera_configs) - 1:
                bpy.ops.object.mode_set(mode='OBJECT')
                mesh_obj.rotation_euler = original_rotation
                logger.info(f"已恢复模型到原始角度，准备处理下一个相机")
        
        # 确保最后退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 处理完所有相机后，恢复模型原始状态
        mesh_obj.location = original_location
        mesh_obj.rotation_euler = original_rotation
        mesh_obj.scale = original_scale
        logger.info("所有相机处理完成，已将模型恢复到原始状态")
        
        # 导出GLB（使用指定的输出路径）
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB')
        logger.info(f"模型已成功导出到 {output_path}")
        
        # 输出状态文件，供Java后端检查
        status_file = os.path.splitext(output_path)[0] + '.status.json'
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump({
                'status': 'success',
                'message': '贴图处理成功完成',
                'model_path': output_path
            }, f, ensure_ascii=False)
        
        logger.info("处理完成，退出程序")
        sys.exit(0)
        
    except Exception as e:
        error_msg = f"处理过程中发生错误: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        # 输出错误状态文件，供Java后端检查
        try:
            status_file = os.path.splitext(output_path)[0] + '.status.json'
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'status': 'error',
                    'message': str(e),
                    'traceback': traceback.format_exc()
                }, f, ensure_ascii=False)
        except:
            pass
            
        sys.exit(1)

except Exception as e:
    # 确保在脚本初始化阶段的错误也被捕获和记录
    error_message = f"脚本初始化错误: {str(e)}\n{traceback.format_exc()}"
    print(error_message)
    
    if log_file:
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(error_message)
        except:
            pass
            
    sys.exit(1)