<template>
    <div v-if="artifact">
        <h1>
            {{ artifact.title }}
            <button
                @click="addToFavorites"
                :disabled="isFavorited || favoriteLoading"
                class="favorite-button"
            >
                {{ buttonText }}
            </button>
        </h1>

        <img :src="artifact.url" :alt="artifact.title" class="detail-image"/>
        <h3>详细信息</h3>
        <pre class="description">{{ artifact.describe }}</pre>
        <h3>分类信息</h3>
        <ul>
            <li>种类 (c0): {{ artifact.c0 }}</li>
        </ul>
    </div>
    <div v-else class="loading-prompt">
        <p>正在加载文物信息...</p>
    </div>
</template>


<script setup>
import {ref,onMounted, computed } from 'vue'
import {useRoute, useRouter } from 'vue-router';
import axios from 'axios'
import { apiUrl } from '@/config/api';

const route = useRoute();
const router = useRouter();
const artifact =ref(null);

const isFavorited =ref(false);
const favoriteLoading = ref(false);

const buttonText = computed(() => {
    if (isFavorited.value) return '已收藏';
    if (favoriteLoading.value) return '收藏中...';
    return '收藏';
});


// onMounted 钩子函数，在页面加载时执行
onMounted(async () => {
    const artifactId = route.params.id;
    if (!artifactId) return;

    // 1. 先获取文物本身的详细信息
    try {
        const response = await axios.get(apiUrl(`/api/artifacts/search?id=${artifactId}`));
        artifact.value = response.data;
    } catch (error) {
        console.error("获取文物详情失败:", error);
        return; // 如果文物信息都加载失败，就没必要继续了
    }

    // 2. 检查用户是否登录（通过本地存储的token判断）
    const token = localStorage.getItem('token');
    if (token) {
        // 3. 如果用户已登录，就向后端查询此物品的收藏状态
        try {
            const statusResponse = await axios.get(
                apiUrl(`/api/user-actions/favorite/status?pid=${artifactId}`),
                { headers: { 'Authorization': token } }
            );
            // 4. 根据后端的返回结果，设置按钮的初始状态
            isFavorited.value = statusResponse.data.isFavorited;
        } catch (error) {
            console.error("获取收藏状态失败:", error);
            // 如果获取状态失败（比如token过期），则默认为未收藏，不做处理
        }
    }
});


const addToFavorites = async()=>{
    if(!artifact.value || favoriteLoading.value){
        alert("文物信息尚未加载完成，无法收藏。");
        return;
    }
    const token = localStorage.getItem('token');
    if(!token){
        alert('请先登录再进行收藏！');
        router.push('/login');
        return;
    }

    favoriteLoading.value = true;
    try{
        await axios.post(
            apiUrl('/api/user-actions/favorite'),
            {pid:artifact.value.pid},
            { headers:{'Authorization':token} }
        );

        isFavorited.value = true;
        alert("收藏成功");
    }catch(error){
        if(error.response && (error.response.status === 401 || error.response.status === 403)){
            alert('登录状态已过期，请重新登录后再收藏。');
            router.push('/login');
        }else{
            alert("收藏过程中发生错误，请稍后再试。");
        }
        console.error("收藏请求错误:", error);
    }finally{
        favoriteLoading.value = false; // 结束加载
    }
};

</script>

<style scoped>
/* 样式部分保持不变 */
.detail-image {
  max-width: 100%;
  width: 500px;
  height: auto;
  display: block;
  margin: 20px auto;
  border-radius: 8px;
}
.description {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 5px;
  white-space: pre-wrap;
  line-height: 1.6;
  font-family: 'Courier New', Courier, monospace;
  color: #333;
}
.loading-prompt {
  text-align: center;
  margin-top: 50px;
  font-size: 1.2rem;
  color: #888;
}
h1, h3 {
  color: #343a40;
  border-bottom: 2px solid #dee2e6;
  padding-bottom: 10px;
  margin-top: 20px;
  margin-bottom: 15px;
}
.favorite-button {
  margin-left: 15px;
  padding: 8px 15px;
  font-size: 0.9rem;
  border: 1px solid #007bff;
  color: #007bff;
  background-color: white;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s ease; /* 过渡效果更平滑 */
  min-width: 90px; /* 防止文本变化时按钮宽度跳动 */
  text-align: center;
}
.favorite-button:hover:not(:disabled) { /* 仅在未禁用时应用悬停效果 */
  background-color: #007bff;
  color: white;
}
.favorite-button:disabled {
  border-color: #ccc;
  color: #ccc;
  background-color: #eee;
  cursor: not-allowed;
}
</style>
