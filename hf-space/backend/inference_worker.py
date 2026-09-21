import os
import sys
import json
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from scipy.special import softmax
import acl
import traceback

# This script is designed to be called as a subprocess.
# It takes two image paths as command-line arguments,
# performs inference, and prints the result as a JSON string.

ACL_MEM_MALLOC_HUGE_FIRST = 0
ACL_MEMCPY_HOST_TO_DEVICE = 1
ACL_MEMCPY_DEVICE_TO_HOST = 2

def preprocess_image(image_path):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    image = Image.open(image_path).convert('RGB')
    tensor = transform(image)
    numpy_array = tensor.numpy().astype(np.float32)
    return np.expand_dims(numpy_array, axis=0)

class AscendModel:
    # This is the known-working AscendModel class from our successful tests
    def __init__(self, model_path, device_id=0):
        self.device_id, self.model_path = device_id, model_path
        self.model_id, self.model_desc, self.context = None, None, None
        self.input_buffers, self.output_buffers = [], []
        self._init_resource()
        self._load_and_prepare_model()
    def _init_resource(self):
        ret = acl.init(); assert ret == 0
        ret = acl.rt.set_device(self.device_id); assert ret == 0
        self.context, ret = acl.rt.create_context(self.device_id); assert ret == 0
    def _load_and_prepare_model(self):
        self.model_id, ret = acl.mdl.load_from_file(self.model_path); assert ret == 0
        self.model_desc = acl.mdl.create_desc(); acl.mdl.get_desc(self.model_desc, self.model_id)
        for i in range(acl.mdl.get_num_inputs(self.model_desc)):
            size = acl.mdl.get_input_size_by_index(self.model_desc, i); buffer, _ = acl.rt.malloc(size, ACL_MEM_MALLOC_HUGE_FIRST); self.input_buffers.append({'buffer': buffer, 'size': size})
        for i in range(acl.mdl.get_num_outputs(self.model_desc)):
            size = acl.mdl.get_output_size_by_index(self.model_desc, i); buffer, _ = acl.rt.malloc(size, ACL_MEM_MALLOC_HUGE_FIRST); self.output_buffers.append({'buffer': buffer, 'size': size})
    def execute(self, inputs):
        input_dataset = acl.mdl.create_dataset()
        for i, data in enumerate(inputs):
            buffer = self.input_buffers[i]['buffer']; data_buffer = acl.create_data_buffer(buffer, data.nbytes); acl.rt.memcpy(buffer, data.nbytes, data.ctypes.data, data.nbytes, ACL_MEMCPY_HOST_TO_DEVICE); acl.mdl.add_dataset_buffer(input_dataset, data_buffer)
        output_dataset = acl.mdl.create_dataset()
        for item in self.output_buffers:
            data_buffer = acl.create_data_buffer(item['buffer'], item['size']); acl.mdl.add_dataset_buffer(output_dataset, data_buffer)
        ret = acl.mdl.execute(self.model_id, input_dataset, output_dataset); assert ret == 0, "Model execute failed"
        outputs = []
        for item in self.output_buffers:
            host_buffer = np.zeros(item['size'], dtype=np.byte); acl.rt.memcpy(host_buffer.ctypes.data, item['size'], item['buffer'], item['size'], ACL_MEMCPY_DEVICE_TO_HOST); outputs.append(host_buffer)
        acl.mdl.destroy_dataset(input_dataset); acl.mdl.destroy_dataset(output_dataset)
        return outputs
    def __del__(self):
        if self.model_id: acl.mdl.unload(self.model_id)
        if self.model_desc: acl.mdl.destroy_desc(self.model_desc)
        for item in self.input_buffers: acl.rt.free(item['buffer'])
        for item in self.output_buffers: acl.rt.free(item['buffer'])
        if self.context: acl.rt.destroy_context(self.context)
        acl.rt.reset_device(self.device_id); acl.finalize()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'Incorrect number of arguments. Expected 2 image paths.'}))
        sys.exit(1)

    img1_path = sys.argv[1]
    img2_path = sys.argv[2]
    om_path = "./viewom.om"

    try:
        model = AscendModel(om_path)
        input1_np = preprocess_image(img1_path)
        input2_np = preprocess_image(img2_path)
        outputs = model.execute([input1_np, input2_np])
        predictions = np.frombuffer(outputs[0], dtype=np.float32).reshape(1, -1)
        probabilities = softmax(predictions, axis=1).flatten() # Flatten to 1D array

        # ==================== NEW: GET TOP 3 PREDICTIONS ====================
        # Use argsort to get the indices that would sort the array in ascending order,
        # then reverse it and take the first 3.
        top_3_indices = np.argsort(probabilities)[::-1][:3]

        top_3_results = []
        for i in top_3_indices:
            top_3_results.append({
                'class': int(i),
                'confidence': f"{probabilities[i]:.4f}"
            })
        # ====================================================================
        
        # Print result as a JSON string to stdout
        # The result is now a list of the top 3 predictions
        print(json.dumps({'predictions': top_3_results}))

    except Exception as e:
        # Print error as a JSON string to stdout
        error_info = {'error': str(e), 'traceback': traceback.format_exc()}
        print(json.dumps(error_info))
        sys.exit(1)