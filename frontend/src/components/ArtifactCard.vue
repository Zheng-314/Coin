<template>
    <RouterLink :to="`/artifact/${artifact.pid}`" class="card-link">
        <div class="card">
            <img :src="artifact.url" :alt="artifact.title" class="card-image" />
            <div class ="card-content">
                <p class="card-title">{{ artifact.title }}</p>
            </div>
        </div>
    </RouterLink>
</template>

<script setup>
// 定义该组件可以接收的“属性”(Props)
defineProps({
    artifact:{
        type:Object,
        required:true
    }
});
</script>

<style scoped>
.card-link {
  text-decoration: none;
  color: inherit;
}
.card {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  background: #fff;
  box-shadow: var(--shadow-sm);
}
.card:hover {
  transform: translateY(-4px);
  border-color: var(--accent-color);
  box-shadow: var(--shadow-md);
}
.card-image {
  width: 100%;
  height: 220px;
  object-fit: contain;
  padding: 10px;
  box-sizing: border-box;
  background: linear-gradient(180deg, #fbf8f3 0%, #f5efe6 100%);
}
.card-content {
  padding: 14px 14px 16px;
}
.card-title {
  margin: 0;
  font-weight: 700;
  color: var(--text-main);
  font-size: 1rem;

  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

</style>
