import { ref } from 'vue'

export function useImageUpload(maxFiles = 3, maxSizeMB = 10) {
  const selectedImages = ref([])
  const imagePreviews = ref([])

  function handleFiles(files) {
    for (const file of files) {
      if (!file.type.startsWith('image/')) continue
      if (file.size > maxSizeMB * 1024 * 1024) continue
      if (selectedImages.value.length >= maxFiles) break
      const reader = new FileReader()
      reader.onload = (e) => { imagePreviews.value.push(e.target.result) }
      reader.readAsDataURL(file)
      selectedImages.value.push(file)
    }
  }

  function clearImages() {
    selectedImages.value = []
    imagePreviews.value = []
  }

  return { selectedImages, imagePreviews, handleFiles, clearImages }
}
