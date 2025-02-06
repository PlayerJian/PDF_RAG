<template>
  <div class="rag-demo">
    <!-- 多轮对话区域 -->
    <div class="conversation-area">
      <div class="message" v-for="(msg, index) in conversation" :key="index">
        <div class="question" v-if="msg.type === 'question'">
          <span class="label">你问：</span>
          {{ msg.content }}
        </div>
        <div class="answer" v-if="msg.type === 'answer'">
          <span class="label">回答：</span>
          <!-- 使用 v-html 绑定流式内容 -->
          <span v-html="msg.streamContent || msg.content"></span>
        </div>
      </div>
    </div>
    <!-- 输入界面 -->
    <div class="input-area">
      <!-- 文件上传部分 -->
      <div class="file-upload">
        <input type="file" @change="handleFileUpload" accept=".pdf" id="file-input" hidden>
        <label for="file-input">
          <i class="fas fa-file-upload"></i>
          {{ file ? file.name : '上传 PDF 文件' }}
        </label>
        <button @click="processPdf" :disabled="!file">处理文件</button>
        <p class="upload-status">{{ uploadStatus }}</p>
      </div>
      <!-- 提问输入部分 -->
      <div class="question-input">
        <input v-model="question" type="text" placeholder="请输入你的问题">
        <button @click="askQuestion" :disabled="!question">提问</button>
        <div id="answer-container"></div>
        <p class="status">{{ status }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      file: null,
      uploadStatus: '',
      question: '',
      status: '',
      conversation: [] // 存储多轮对话信息
    };
  },
  methods: {
    handleFileUpload(event) {
      this.file = event.target.files[0];
    },
    async processPdf() {
      if (!this.file) {
        this.uploadStatus = '请选择一个 PDF 文件';
        return;
      }

      const formData = new FormData();
      formData.append('file', this.file);

      try {
        const response = await axios.post('/process_pdf/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        this.uploadStatus = response.data.message;
      } catch (error) {
        this.uploadStatus = error.response.data.error;
      }
    },
    async askQuestion() {
      if (!this.question) {
        this.status = '请输入一个问题';
        return;
      }
      const currentQuestionIndex = this.conversation.length;
      this.conversation.push({ type: 'question', content: this.question });
      this.conversation.push({ type: 'answer', content: '', streamContent: '' });

      try {
        this.status = '生成回答中...';
        const response = await fetch('/query_answer/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ question: this.question })
        });

        if (!response.ok) {
          throw new Error('请求失败');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let isReading = true;
        while (isReading) {
          const { done, value } = await reader.read();
          if (done) {
            isReading = false;
          } else {
            const chunk = decoder.decode(value, { stream: true });
            this.conversation[currentQuestionIndex + 1].streamContent += chunk;
          }
        }
        this.conversation[currentQuestionIndex + 1].content = this.conversation[currentQuestionIndex + 1].streamContent;
        this.status = '完成!';
        this.question = '';
      } catch (error) {
        this.conversation.push({ type: 'answer', content: `遇到错误: ${error.response.data.error}` });
        this.status = '遇到错误';
      }
    }
  }
};
</script>

<style scoped>
.rag-demo {
  display: flex;
  flex-direction: column;
  height: 100vh; /* 占满整个浏览器高度 */
  font-family: Arial, sans-serif;
}

.conversation-area {
  flex: 0.7; /* 占据剩余可用空间 */
  overflow-y: auto; /* 内容超出时显示滚动条 */
  padding: 10px;
  background-color: #f9f9f9;
  border-bottom: 1px solid #ddd;
}

.message {
  margin-bottom: 15px;
}

.question,
.answer {
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 5px;
}

.question {
  background-color: #e0f7fa;
}

.answer {
  background-color: #f1f8e9;
}

.label {
  font-weight: bold;
}

.input-area {
  padding: 10px; /* 减少输入区域的内边距 */
  display: flex;
  flex-direction: column;
  gap: 10px; /* 减少元素之间的间距 */
  flex-shrink: 0; /* 防止输入区域缩小 */
}

.file-upload {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-upload label {
  cursor: pointer;
  color: #007bff;
}

.file-upload button {
  padding: 6px 12px; /* 减小按钮的内边距 */
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.file-upload button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.upload-status {
  margin-left: 10px;
  color: #666;
}

.question-input {
  display: flex;
  align-items: center;
  gap: 10px;
}

.question-input input {
  flex: 1;
  padding: 6px; /* 减小输入框的内边距 */
  border: 1px solid #ccc;
  border-radius: 5px;
}

.question-input button {
  padding: 6px 12px; /* 减小按钮的内边距 */
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.question-input button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.status {
  margin-left: 10px;
  color: #666;
}
</style>