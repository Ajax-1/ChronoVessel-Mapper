<template>
  <div class="texturing-container">
    <h2>舰船贴图系统</h2>
    
    <!-- 选择区域 -->
    <div class="selection-area">
      <!-- 船型选择 -->
      <div class="form-group">
        <label for="shipType">选择船型：</label>
        <select 
          id="shipType" 
          v-model="selectedShipType" 
          class="form-control"
          @change="handleShipTypeChange">
          <option value="">-- 请选择船型 --</option>
          <option 
            v-for="ship in shipTypes" 
            :key="ship.id" 
            :value="ship.id">
            {{ ship.name }}
          </option>
        </select>
      </div>
      
      <!-- 日期选择 -->
      <div class="form-group">
        <label for="textureDate">选择纹理日期：</label>
        <select 
          id="textureDate" 
          v-model="selectedDateId" 
          class="form-control"
          :disabled="!selectedShipType">
          <option value="">-- 请选择日期 --</option>
          <option 
            v-for="date in availableDates" 
            :key="date.id" 
            :value="date.id">
            {{ date.date }}
          </option>
        </select>
      </div>
      
      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button 
          @click="processTexturing" 
          :disabled="!canProcess"
          class="primary-button">
          生成贴图模型
        </button>
        
        <div v-if="showUpload" class="upload-section">
          <h3>或者直接上传文件</h3>
          
          <div class="form-group">
            <label for="modelFile">3D模型文件：</label>
            <input 
              type="file" 
              id="modelFile" 
              @change="handleModelFileChange" 
              accept=".ply,.obj,.fbx,.stl,.glb,.gltf" />
          </div>
          
          <div class="form-group">
            <label for="topTextureFile">顶部纹理图片：</label>
            <input 
              type="file" 
              id="topTextureFile" 
              @change="handleTopTextureFileChange" 
              accept=".jpg,.jpeg,.png" />
          </div>
          
          <div class="form-group">
            <label for="sideTextureFile">侧面纹理图片：</label>
            <input 
              type="file" 
              id="sideTextureFile" 
              @change="handleSideTextureFileChange" 
              accept=".jpg,.jpeg,.png" />
          </div>
          
          <button 
            @click="processUploadedFiles" 
            :disabled="!canUploadProcess"
            class="secondary-button">
            处理上传文件
          </button>
        </div>
      </div>
    </div>
    
    <!-- 状态和结果区域 -->
    <div class="result-area">
      <!-- 处理状态 -->
      <div v-if="processing" class="processing-status">
        <div class="spinner"></div>
        <p>正在处理贴图，请稍候...</p>
      </div>
      
      <!-- 错误信息 -->
      <div v-if="error" class="error-message">
        <h3>处理出错</h3>
        <p>{{ errorMessage }}</p>
      </div>
      
      <!-- 结果展示区 -->
      <div v-if="modelUrl" class="model-container">
        <h3>贴图处理完成</h3>
        <model-viewer
          :src="modelUrl"
          camera-controls
          auto-rotate
          shadow-intensity="1"
          environment-image="neutral"
          exposure="1"
        ></model-viewer>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { ref, computed, onMounted } from 'vue';
import 'model-viewer';

export default {
  name: 'ShipTextureApp',
  
  setup() {
    // 状态变量
    const shipTypes = ref([]);
    const selectedShipType = ref('');
    const availableDates = ref([]);
    const selectedDateId = ref('');
    const processing = ref(false);
    const error = ref(false);
    const errorMessage = ref('');
    const modelUrl = ref('');
    const showUpload = ref(false);
    
    // 文件上传变量
    const modelFile = ref(null);
    const topTextureFile = ref(null);
    const sideTextureFile = ref(null);
    
    // API基础URL
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
    
    // 计算属性
    const canProcess = computed(() => 
      selectedShipType.value && selectedDateId.value && !processing.value
    );
    
    const canUploadProcess = computed(() => 
      modelFile.value && topTextureFile.value && sideTextureFile.value && !processing.value
    );
    
    // 生命周期钩子
    onMounted(async () => {
      await fetchShipTypes();
    });
    
    // 方法
    const fetchShipTypes = async () => {
      try {
        const response = await axios.get(`${apiBaseUrl}/api/ships`);
        shipTypes.value = response.data;
      } catch (err) {
        console.error('获取船型失败:', err);
        error.value = true;
        errorMessage.value = '获取船型数据失败，请稍后重试';
      }
    };
    
    const handleShipTypeChange = async () => {
      if (!selectedShipType.value) {
        availableDates.value = [];
        return;
      }
      
      try {
        const response = await axios.get(
          `${apiBaseUrl}/api/ships/${selectedShipType.value}/dates`
        );
        availableDates.value = response.data;
      } catch (err) {
        console.error('获取日期数据失败:', err);
        error.value = true;
        errorMessage.value = '获取纹理日期数据失败，请稍后重试';
      }
    };
    
    const processTexturing = async () => {
      processing.value = true;
      error.value = false;
      modelUrl.value = '';
      
      try {
        const response = await axios.post(`${apiBaseUrl}/api/texturing`, {
          shipId: selectedShipType.value,
          dateId: selectedDateId.value
        });
        
        handleProcessingResult(response.data);
      } catch (err) {
        console.error('贴图处理请求失败:', err);
        error.value = true;
        errorMessage.value = '贴图处理请求失败，请稍后重试';
      } finally {
        processing.value = false;
      }
    };
    
    // 文件上传处理
    const handleModelFileChange = (event) => {
      modelFile.value = event.target.files[0];
    };
    
    const handleTopTextureFileChange = (event) => {
      topTextureFile.value = event.target.files[0];
    };
    
    const handleSideTextureFileChange = (event) => {
      sideTextureFile.value = event.target.files[0];
    };
    
    const processUploadedFiles = async () => {
      if (!modelFile.value || !topTextureFile.value || !sideTextureFile.value) {
        error.value = true;
        errorMessage.value = '请上传所有必需的文件';
        return;
      }
      
      processing.value = true;
      error.value = false;
      modelUrl.value = '';
      
      try {
        const formData = new FormData();
        formData.append('model', modelFile.value);
        formData.append('topTexture', topTextureFile.value);
        formData.append('sideTexture', sideTextureFile.value);
        
        const response = await axios.post(
          `${apiBaseUrl}/api/texturing/upload`, 
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          }
        );
        
        handleProcessingResult(response.data);
      } catch (err) {
        console.error('文件上传贴图处理失败:', err);
        error.value = true;
        errorMessage.value = '文件上传处理失败，请稍后重试';
      } finally {
        processing.value = false;
      }
    };
    
    const handleProcessingResult = (result) => {
      if (result.success) {
        modelUrl.value = result.modelUrl;
      } else {
        error.value = true;
        errorMessage.value = result.message || '处理失败，未返回错误信息';
      }
    };
    
    const toggleUploadSection = () => {
      showUpload.value = !showUpload.value;
    };
    
    return {
      shipTypes,
      selectedShipType,
      availableDates,
      selectedDateId,
      processing,
      error,
      errorMessage,
      modelUrl,
      showUpload,
      modelFile,
      topTextureFile,
      sideTextureFile,
      canProcess,
      canUploadProcess,
      fetchShipTypes,
      handleShipTypeChange,
      processTexturing,
      handleModelFileChange,
      handleTopTextureFileChange,
      handleSideTextureFileChange,
      processUploadedFiles,
      toggleUploadSection
    };
  }
}
</script>

<style scoped>
.texturing-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #2c3e50;
}

.selection-area {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-top: 20px;
}

button {
  padding: 12px 20px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.primary-button {
  background-color: #4caf50;
  color: white;
}

.primary-button:hover:not(:disabled) {
  background-color: #45a049;
}

.secondary-button {
  background-color: #2196f3;
  color: white;
}

.secondary-button:hover:not(:disabled) {
  background-color: #0b7dda;
}

.upload-section {
  border-top: 1px solid #ddd;
  padding-top: 20px;
  margin-top: 20px;
}

.processing-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 2s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  background-color: #ffebee;
  color: #c62828;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.model-container {
  height: 500px;
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

model-viewer {
  width: 100%;
  height: 100%;
  background-color: #f5f5f5;
}
</style> 