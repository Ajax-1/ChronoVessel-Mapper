package com.shipproject.controller;

import com.shipproject.dto.ShipTypeDTO;
import com.shipproject.dto.TextureDateDTO;
import com.shipproject.dto.TexturingRequestDTO;
import com.shipproject.dto.TexturingResponseDTO;
import com.shipproject.service.ShipService;
import com.shipproject.service.TexturingService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*") // 允许跨域请求，生产环境应该设置具体的域名
public class TexturingController {

    private static final Logger logger = LoggerFactory.getLogger(TexturingController.class);

    @Autowired
    private ShipService shipService;

    @Autowired
    private TexturingService texturingService;

    /**
     * 获取所有船型
     */
    @GetMapping("/ships")
    public ResponseEntity<List<ShipTypeDTO>> getAllShipTypes() {
        logger.info("获取所有船型");
        return ResponseEntity.ok(shipService.getAllShipTypes());
    }

    /**
     * 获取特定船型的可用纹理日期
     */
    @GetMapping("/ships/{shipId}/dates")
    public ResponseEntity<List<TextureDateDTO>> getDatesForShipType(@PathVariable Long shipId) {
        logger.info("获取船型ID {} 的可用纹理日期", shipId);
        return ResponseEntity.ok(shipService.getTexturesForShipType(shipId));
    }

    /**
     * 处理贴图请求 - 根据IDs
     */
    @PostMapping("/texturing")
    public ResponseEntity<TexturingResponseDTO> processTexturing(@RequestBody TexturingRequestDTO request) {
        logger.info("接收到贴图请求: 船型ID={}, 日期ID={}", request.getShipId(), request.getDateId());
        
        try {
            // 异步处理贴图
            CompletableFuture<TexturingService.TexturingResult> future = 
                    texturingService.processTexturingByIds(request.getShipId(), request.getDateId());
            
            // 等待结果返回（实际生产环境可能需要使用WebSocket通知用户结果）
            TexturingService.TexturingResult result = future.get();
            
            // 构建响应
            TexturingResponseDTO response = new TexturingResponseDTO();
            response.setSuccess(result.isSuccess());
            response.setModelUrl(result.getModelUrl());
            response.setMessage(result.getMessage());
            
            return ResponseEntity.ok(response);
        } catch (InterruptedException | ExecutionException e) {
            logger.error("贴图处理失败", e);
            
            TexturingResponseDTO response = new TexturingResponseDTO();
            response.setSuccess(false);
            response.setMessage("处理失败: " + e.getMessage());
            
            return ResponseEntity.ok(response);
        }
    }

    /**
     * 处理贴图请求 - 直接上传文件
     */
    @PostMapping("/texturing/upload")
    public ResponseEntity<TexturingResponseDTO> processUploadedFiles(
            @RequestParam("model") MultipartFile modelFile,
            @RequestParam("topTexture") MultipartFile topTextureFile,
            @RequestParam("sideTexture") MultipartFile sideTextureFile) {
        
        logger.info("接收到文件上传贴图请求: 模型={}, 顶部纹理={}, 侧面纹理={}",
                modelFile.getOriginalFilename(),
                topTextureFile.getOriginalFilename(),
                sideTextureFile.getOriginalFilename());
        
        try {
            // 异步处理贴图
            CompletableFuture<TexturingService.TexturingResult> future = 
                    texturingService.processUploadedFiles(modelFile, topTextureFile, sideTextureFile);
            
            // 等待结果
            TexturingService.TexturingResult result = future.get();
            
            // 构建响应
            TexturingResponseDTO response = new TexturingResponseDTO();
            response.setSuccess(result.isSuccess());
            response.setModelUrl(result.getModelUrl());
            response.setMessage(result.getMessage());
            
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            logger.error("文件上传贴图处理失败", e);
            
            TexturingResponseDTO response = new TexturingResponseDTO();
            response.setSuccess(false);
            response.setMessage("处理失败: " + e.getMessage());
            
            return ResponseEntity.ok(response);
        }
    }

    /**
     * 贴图处理状态查询（用于长时间处理的轮询）
     */
    @GetMapping("/texturing/{jobId}/status")
    public ResponseEntity<TexturingResponseDTO> getTexturingStatus(@PathVariable String jobId) {
        // 此方法用于前端轮询查询贴图任务的状态
        // 实际实现应该根据jobId在数据库或缓存中查找任务状态
        // 这里只是示例框架
        
        logger.info("查询贴图作业状态: jobId={}", jobId);
        
        TexturingResponseDTO response = new TexturingResponseDTO();
        // 此处应该根据真实情况设置状态
        response.setSuccess(true);
        response.setStatus("processing");  // 可能的状态：queued, processing, completed, failed
        response.setMessage("贴图处理中...");
        
        return ResponseEntity.ok(response);
    }
} 