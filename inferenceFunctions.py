
"""
class TextVectorizers():
    def __init__(self, vectorizer_config_path, vectorize_vocabulary_path):

        with open(vectorizer_config_path, "r") as json_file:
            config = json.load(json_file)

        self.vectorizer = tf.keras.layers.TextVectorization.from_config(config)

        with open(vectorize_vocabulary_path, "r") as vocab_file:
            vocabulary = vocab_file.read().splitlines()

        self.vectorizer.set_vocabulary(vocabulary)

    def vectorize_text(self, text):
        return self.vectorizer(text).numpy()

"""

def toxicity_inference(pipeline, text):
    
    label_positions_dict = {'toxic': 0, 'neutral': 1}
    try:
        output = pipeline(text)
        
        """
        if output[0]['label'] == 'toxic':
            print(f"\nToxic text: {text}\n")
        """
        return label_positions_dict[output[0]['label']]
        
        

    except:
        print("Project Failed")
        return 'FAILED'

def emotions_inference(pipeline, text):
    label_positions_dict = {'anger': 0, 'disgust': 1, 'fear': 2, 'joy': 3, 'neutral': 4, 'sadness': 5, 'surprise': 6}

    try:
        
        output = pipeline(text)
        
        """
        if output[0]['label'] == 'joy':
            print(f"Joy text: {text}")


        if output[0]['label'] == 'surprise':
            print(f"Surprise text: {text}")

        if output[0]['label'] == 'disgust':
            print(f"Disgust text: {text}")
        """

        return label_positions_dict[output[0]['label']]
        #If its 'anger', return 0
        #0 will be the position to add 1 point to
        
    except Exception as e:
        print("InferenceFunction had an error!")
        print(e)
        return 'FAILED'
    
        #If it returns 0 - means its negative
        #If it returns 1 - means its neutral
        #If it returns 2 - means its positive
def sentiment_classification_inference(pipeline, text):
    #Returns negative, neutral, or positive based on the vectorized words. This can sometimes not capture the true sentiment. 
    
    try:
        output = pipeline(text)
        broken_label = output[0]['label'].split('_')
        pos = int(broken_label[-1])
        """
        if pos == 0:
            print(f"Neg Text: {text}")
        """
        
        return pos
    except:
        return 'FAILED'
    
        #If it returns 0 - means its negative
        #If it returns 1 - means its neutral
        #If it returns 2 - means its positive

"""
def inference_onnx_model(model_path, batch_size, input_data):
    try:
        # Load the ONNX model
        session = onnxruntime.InferenceSession(model_path)

        # Run inference with the provided input data
        batch_num = math.ceil(len(input_data) / batch_size)

        start_index = 0
        end_index = batch_size - 0

        #3 batches

        #1 - 32: i = 0
        #2 - 32: i = 1
        #3 - 20


        for i in range(batch_num):
            inputs = input_data[start_index: end_index]
            output = session.run(None, input_data)
            yield output  # Return all outputs as a list'

            start_index = end_index
            if (i + 2) == batch_num: #If the next batch is the last batch
                end_index = -1

            
    except Exception as e:
        print(f"Error running inference: {e}")
        yield None

"""