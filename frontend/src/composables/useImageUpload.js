import { ref } from "vue";

/** 图片上传和预览 composable */
export function useImageUpload(maxFiles = 10, maxSizeMB = 10) {
  const selectedImages = ref([]);
  const imagePreviews = ref([]);
  const uploadError = ref(null);

  const MAX_SIZE = maxSizeMB * 1024 * 1024;

  function handleFiles(files) {
    uploadError.value = null;
    const validFiles = [];

    for (const file of files) {
      if (!file.type.startsWith("image/")) continue;
      if (file.size > MAX_SIZE) {
        uploadError.value = `图片大小不能超过 ${maxSizeMB}MB`;
        continue;
      }
      if (selectedImages.value.length + validFiles.length >= maxFiles) break;
      validFiles.push(file);
    }

    for (const file of validFiles) {
      const reader = new FileReader();
      reader.onload = (e) => {
        imagePreviews.value.push(e.target.result);
      };
      reader.readAsDataURL(file);
      selectedImages.value.push(file);
    }
  }

  function removeImage(index) {
    selectedImages.value.splice(index, 1);
    imagePreviews.value.splice(index, 1);
  }

  function clearImages() {
    selectedImages.value = [];
    imagePreviews.value = [];
  }

  return { selectedImages, imagePreviews, uploadError, handleFiles, removeImage, clearImages };
}
