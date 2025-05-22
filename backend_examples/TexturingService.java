package com.shipproject.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

@Service
public class TexturingService {

    private static final Logger logger = LoggerFactory.getLogger(TexturingService.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${app.blender.path}")
    private String blenderPath;

    @Value("${app.blender.script}")
    private String blenderScriptPath;

    @Value("${app.temp.dir}")
    private String tempDir;

    @Value("${app.output.dir}")
    private String outputDir;

    @Value("${app.output.baseUrl}")
    private String outputBaseUrl;

    @Autowired
    private ShipModelRepository shipModelRepository;

    @Autowired
    private TextureRepository textureRepository;

    /**
     * 根据船型ID和日期ID处理贴图
     */
    public CompletableFuture<TexturingResult> processTexturingByIds(Long shipId, Long dateId) {
        try {
            // 1. 从数据库获取模型和纹理数据
            ShipModel shipModel = shipModelRepository.findById(shipId)
                    .orElseThrow(() -> new ResourceNotFoundException("找不到指定ID的船型模型: " + shipId));
            
            Texture texture = textureRepository.findById(dateId)
                    .orElseThrow(() -> new ResourceNotFoundException("找不到指定ID的纹理: " + dateId));

            // 2. 将数据保存到临时文件
            String jobId = UUID.randomUUID().toString();
            Path workDir = Paths.get(tempDir, jobId);
            Files.createDirectories(workDir);

            // 3. 保存模型文件
            Path modelPath = workDir.resolve("model.ply");
            Files.write(modelPath, shipModel.getModelData());

            // 4. 保存顶部和侧面纹理图片
            Path topTexturePath = workDir.resolve("texture_top.jpg");
            Path sideTexturePath = workDir.resolve("texture_side.jpg");
            Files.write(topTexturePath, texture.getTopTextureData());
            Files.write(sideTexturePath, texture.getSideTextureData());

            // 5. 设置输出路径
            Path outputPath = Paths.get(outputDir, jobId, "result.glb");
            Files.createDirectories(outputPath.getParent());

            // 6. 设置日志路径
            Path logPath = workDir.resolve("process.log");

            // 7. 启动异步处理
            return CompletableFuture.supplyAsync(() -> {
                try {
                    // 调用Blender脚本进行处理
                    boolean success = executeBlenderScript(
                            modelPath.toString(),
                            topTexturePath.toString(),
                            sideTexturePath.toString(),
                            outputPath.toString(),
                            logPath.toString()
                    );

                    if (success) {
                        // 检查状态文件
                        Path statusFile = Paths.get(outputPath.toString().replace(".glb", ".status.json"));
                        Map<String, Object> status = objectMapper.readValue(statusFile.toFile(), Map.class);

                        if ("success".equals(status.get("status"))) {
                            // 成功，返回处理结果
                            return new TexturingResult(
                                    true,
                                    outputBaseUrl + "/" + jobId + "/result.glb",
                                    (String) status.get("message")
                            );
                        } else {
                            // 处理过程中出错
                            return new TexturingResult(
                                    false,
                                    null,
                                    (String) status.get("message")
                            );
                        }
                    } else {
                        // 执行失败
                        return new TexturingResult(
                                false,
                                null,
                                "Blender处理执行失败"
                        );
                    }
                } catch (Exception e) {
                    logger.error("处理贴图时发生错误", e);
                    return new TexturingResult(
                            false,
                            null,
                            "处理错误: " + e.getMessage()
                    );
                }
            });
        } catch (Exception e) {
            logger.error("准备贴图处理时发生错误", e);
            CompletableFuture<TexturingResult> future = new CompletableFuture<>();
            future.completeExceptionally(e);
            return future;
        }
    }

    /**
     * 直接使用上传的文件进行贴图处理
     */
    public CompletableFuture<TexturingResult> processUploadedFiles(
            MultipartFile modelFile,
            MultipartFile topTextureFile,
            MultipartFile sideTextureFile
    ) {
        try {
            // 1. 创建临时工作目录
            String jobId = UUID.randomUUID().toString();
            Path workDir = Paths.get(tempDir, jobId);
            Files.createDirectories(workDir);

            // 2. 保存上传的文件
            Path modelPath = workDir.resolve(modelFile.getOriginalFilename());
            Path topTexturePath = workDir.resolve(topTextureFile.getOriginalFilename());
            Path sideTexturePath = workDir.resolve(sideTextureFile.getOriginalFilename());

            modelFile.transferTo(modelPath.toFile());
            topTextureFile.transferTo(topTexturePath.toFile());
            sideTextureFile.transferTo(sideTexturePath.toFile());

            // 3. 设置输出和日志路径
            Path outputPath = Paths.get(outputDir, jobId, "result.glb");
            Files.createDirectories(outputPath.getParent());
            Path logPath = workDir.resolve("process.log");

            // 4. 启动异步处理
            return CompletableFuture.supplyAsync(() -> {
                try {
                    boolean success = executeBlenderScript(
                            modelPath.toString(),
                            topTexturePath.toString(),
                            sideTexturePath.toString(),
                            outputPath.toString(),
                            logPath.toString()
                    );

                    if (success) {
                        Path statusFile = Paths.get(outputPath.toString().replace(".glb", ".status.json"));
                        Map<String, Object> status = objectMapper.readValue(statusFile.toFile(), Map.class);

                        if ("success".equals(status.get("status"))) {
                            return new TexturingResult(
                                    true,
                                    outputBaseUrl + "/" + jobId + "/result.glb",
                                    (String) status.get("message")
                            );
                        } else {
                            return new TexturingResult(
                                    false,
                                    null,
                                    (String) status.get("message")
                            );
                        }
                    } else {
                        return new TexturingResult(
                                false,
                                null,
                                "Blender处理执行失败"
                        );
                    }
                } catch (Exception e) {
                    logger.error("处理贴图时发生错误", e);
                    return new TexturingResult(
                            false,
                            null,
                            "处理错误: " + e.getMessage()
                    );
                }
            });
        } catch (Exception e) {
            logger.error("准备贴图处理时发生错误", e);
            CompletableFuture<TexturingResult> future = new CompletableFuture<>();
            future.completeExceptionally(e);
            return future;
        }
    }

    /**
     * 执行Blender脚本进行贴图处理
     */
    private boolean executeBlenderScript(
            String modelPath,
            String topTexturePath,
            String sideTexturePath,
            String outputPath,
            String logPath
    ) throws IOException, InterruptedException {
        // 构建命令
        ProcessBuilder pb = new ProcessBuilder(
                blenderPath,
                "--background",
                "--python", blenderScriptPath,
                "--",
                modelPath,
                topTexturePath,
                sideTexturePath,
                outputPath,
                logPath
        );

        // 设置工作目录
        pb.directory(new File(System.getProperty("user.dir")));

        // 合并标准错误和标准输出
        pb.redirectErrorStream(true);

        // 将输出写入日志文件
        pb.redirectOutput(new File(logPath));

        // 启动进程
        logger.info("执行贴图命令: {}", String.join(" ", pb.command()));
        Process process = pb.start();

        // 等待进程完成，设置超时时间
        boolean completed = process.waitFor(10, TimeUnit.MINUTES);
        if (!completed) {
            // 超时，强制终止
            process.destroyForcibly();
            logger.error("贴图处理超时，已强制终止");
            return false;
        }

        // 检查退出代码
        int exitCode = process.exitValue();
        logger.info("贴图处理完成，退出代码: {}", exitCode);
        return exitCode == 0;
    }

    /**
     * 贴图结果类
     */
    public static class TexturingResult {
        private final boolean success;
        private final String modelUrl;
        private final String message;

        public TexturingResult(boolean success, String modelUrl, String message) {
            this.success = success;
            this.modelUrl = modelUrl;
            this.message = message;
        }

        public boolean isSuccess() {
            return success;
        }

        public String getModelUrl() {
            return modelUrl;
        }

        public String getMessage() {
            return message;
        }
    }

    /**
     * 资源未找到异常
     */
    public static class ResourceNotFoundException extends RuntimeException {
        public ResourceNotFoundException(String message) {
            super(message);
        }
    }
} 