<template>
  <main class="home-page">
    <section class="hero coin-panel">
      <h1>海量钱币数据库，专业鉴定支持</h1>
      <p>聚合钱币图谱、鉴定经验与历史文化知识，帮助你更高效地识别与理解珍贵藏品。</p>
      <div class="search-bar">
        <input type="text" v-model="searchQuery" placeholder="按名称搜索钱币..." @keyup.enter="startNewSearch" />
        <button @click="startNewSearch">立即搜索</button>
      </div>
      <div class="filter-bar">
        <select v-model="selectedDynasty" @change="startNewSearch">
          <option value="">全部朝代</option>
          <option v-for="item in filterOptions.dynasties" :key="item" :value="item">{{ item }}</option>
        </select>
        <input
          v-model.number="yearStart"
          type="number"
          placeholder="起始年份"
          :min="filterOptions.yearMin || undefined"
          :max="filterOptions.yearMax || undefined"
          @keyup.enter="startNewSearch"
        />
        <input
          v-model.number="yearEnd"
          type="number"
          placeholder="结束年份"
          :min="filterOptions.yearMin || undefined"
          :max="filterOptions.yearMax || undefined"
          @keyup.enter="startNewSearch"
        />
        <select v-model="selectedProvince" @change="startNewSearch">
          <option value="">全部省份</option>
          <option v-for="item in filterOptions.provinces" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="selectedGrade" @change="startNewSearch">
          <option value="">全部级别</option>
          <option v-for="item in filterOptions.grades" :key="item" :value="item">{{ item }}</option>
        </select>
        <button class="reset-button" @click="resetFilters">重置筛选</button>
      </div>
    </section>

    <div class="header-controls">
      <h2>钱币数据库</h2>
      <div class="category-bar">
        <button
          v-for="cat in categories"
          :key="cat.value || 'all'"
          class="cat-chip"
          :class="{ active: selectedCategory === cat.value }"
          @click="selectCategory(cat.value)"
        >
          {{ cat.label }}
        </button>
      </div>
    </div>

    <div class="artifacts-grid">
      <ArtifactCard v-for="item in artifacts" :key="item.pid" :artifact="item" />
    </div>

    <div v-if="isLoading" class="loading-prompt">正在加载更多...</div>
    <div v-if="!hasMore && artifacts.length > 0" class="loading-prompt">没有更多数据了</div>
    <div v-if="!isLoading && artifacts.length === 0" class="loading-prompt">没有找到匹配的钱币。</div>
  </main>
</template>

<script setup>
defineOptions({
  name: 'HomeView'
});

import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import ArtifactCard from '@/components/ArtifactCard.vue';
import { apiUrl } from '@/config/api';

const artifacts = ref([]);
const currentPage = ref(1);
const isLoading = ref(false);
const hasMore = ref(true);
const searchQuery = ref('');
const selectedCategory = ref('');
const categories = ref([{ value: '', label: '全部' }]);
const selectedDynasty = ref('');
const yearStart = ref(null);
const yearEnd = ref(null);
const selectedProvince = ref('');
const selectedGrade = ref('');
const filterOptions = ref({
  dynasties: [],
  provinces: [],
  grades: [],
  yearMin: null,
  yearMax: null
});

const loadCategories = async () => {
  try {
    const response = await axios.get(apiUrl('/api/artifacts/classification'));
    const raw = response.data || {};
    const top = Object.values(raw).map((item) => ({
      value: item.c0 || '',
      label: item.unicode || item.c0 || '未分类'
    }));
    categories.value = [{ value: '', label: '全部' }, ...top.filter((x) => x.value)];
  } catch (error) {
    console.error('加载分类失败：', error);
    categories.value = [{ value: '', label: '全部' }];
  }
};

const fetchArtifacts = async () => {
  if (isLoading.value || !hasMore.value) return;

  isLoading.value = true;
  try {
    let url = apiUrl(`/api/artifacts/searchItems?page=${currentPage.value}&limit=20`);
    if (searchQuery.value.trim()) {
      url += `&q=${encodeURIComponent(searchQuery.value.trim())}`;
    }
    if (selectedCategory.value) {
      url += `&c0=${encodeURIComponent(selectedCategory.value)}`;
    }
    if (selectedDynasty.value) {
      url += `&dynasty=${encodeURIComponent(selectedDynasty.value)}`;
    }
    if (selectedProvince.value) {
      url += `&province=${encodeURIComponent(selectedProvince.value)}`;
    }
    if (selectedGrade.value) {
      url += `&grade=${encodeURIComponent(selectedGrade.value)}`;
    }
    if (yearStart.value !== null && yearStart.value !== '' && !Number.isNaN(Number(yearStart.value))) {
      url += `&year_start=${encodeURIComponent(Number(yearStart.value))}`;
    }
    if (yearEnd.value !== null && yearEnd.value !== '' && !Number.isNaN(Number(yearEnd.value))) {
      url += `&year_end=${encodeURIComponent(Number(yearEnd.value))}`;
    }

    const response = await axios.get(url);
    if (response.data.length > 0) {
      artifacts.value = [...artifacts.value, ...response.data];
      currentPage.value++;
    } else {
      hasMore.value = false;
    }
  } catch (error) {
    console.error('获取钱币列表失败：', error);
  } finally {
    isLoading.value = false;
  }
};

const loadFilterOptions = async () => {
  try {
    const response = await axios.get(apiUrl('/api/artifacts/filters'));
    const data = response.data || {};
    filterOptions.value = {
      dynasties: data.dynasties || [],
      provinces: data.provinces || [],
      grades: data.grades || [],
      yearMin: data.year_min ?? null,
      yearMax: data.year_max ?? null
    };
  } catch (error) {
    console.error('加载筛选项失败：', error);
    filterOptions.value = { dynasties: [], provinces: [], grades: [], yearMin: null, yearMax: null };
  }
};

const startNewSearch = () => {
  if (yearStart.value !== null && yearEnd.value !== null && yearStart.value > yearEnd.value) {
    const temp = yearStart.value;
    yearStart.value = yearEnd.value;
    yearEnd.value = temp;
  }
  artifacts.value = [];
  currentPage.value = 1;
  hasMore.value = true;
  fetchArtifacts();
};

const selectCategory = (c0) => {
  if (selectedCategory.value === c0) return;
  selectedCategory.value = c0;
  startNewSearch();
};

const resetFilters = () => {
  selectedDynasty.value = '';
  yearStart.value = null;
  yearEnd.value = null;
  selectedProvince.value = '';
  selectedGrade.value = '';
  startNewSearch();
};

const handleScroll = () => {
  if (window.innerHeight + window.scrollY >= document.documentElement.offsetHeight - 100) {
    fetchArtifacts();
  }
};

onMounted(() => {
  loadCategories();
  loadFilterOptions();
  fetchArtifacts();
  window.addEventListener('scroll', handleScroll);
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<style scoped>
.home-page {
  display: grid;
  gap: 22px;
}

.hero {
  padding: 28px 26px;
  background: linear-gradient(120deg, #fff 0%, #f8f1ea 70%, #f3e7d8 100%);
}

.hero h1 {
  margin: 0;
  color: var(--primary-color);
}

.hero p {
  margin: 10px 0 0;
  color: var(--text-secondary);
}

.header-controls {
  padding: 0 6px;
}

.header-controls h2 {
  margin: 0;
  color: var(--text-main);
}

.category-bar {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cat-chip {
  border: 1px solid var(--border-color);
  background: #fff;
  color: var(--text-main);
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 0.88rem;
  transition: all 0.2s ease;
}

.cat-chip:hover {
  border-color: var(--accent-color);
  background: #fdf8f2;
}

.cat-chip.active {
  background: var(--primary-color);
  color: #fff;
  border-color: var(--primary-color);
}

.search-bar {
  margin-top: 18px;
  display: flex;
  justify-content: flex-start;
  gap: 10px;
}

.search-bar input {
  width: min(520px, 100%);
  padding: 11px 14px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  font-size: 1rem;
  outline: none;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s ease;
}

.search-bar input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(139, 58, 58, 0.12);
}

.search-bar button {
  padding: 10px 22px;
  border: none;
  background-color: var(--primary-color);
  color: white;
  border-radius: 999px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.search-bar button:hover {
  background-color: var(--primary-hover);
  transform: translateY(-1px);
}

.filter-bar {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.filter-bar select,
.filter-bar input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  font-size: 0.92rem;
  background: #fff;
  color: var(--text-main);
  outline: none;
}

.filter-bar select:focus,
.filter-bar input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(139, 58, 58, 0.1);
}

.reset-button {
  border: 1px solid var(--border-color);
  background: #fff;
  color: var(--text-main);
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reset-button:hover {
  border-color: var(--accent-color);
  background: #fdf8f2;
}

.artifacts-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

@media (max-width: 1280px) {
  .artifacts-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .artifacts-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.loading-prompt {
  text-align: center;
  color: var(--text-secondary);
  padding: 12px 0;
}

@media (max-width: 760px) {
  .hero {
    padding: 20px 16px;
  }
  .search-bar {
    flex-direction: column;
  }
  .search-bar button {
    width: 100%;
  }
  .filter-bar {
    grid-template-columns: 1fr;
  }
  .artifacts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
