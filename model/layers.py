#-*- coding:utf-8 -*-
import tensorflow as tf

class Dense(tf.keras.layers.Layer):
    def __init__(self, units, input_dims=5, **kwargs):
        super(Dense, self).__init__(name='Linear', **kwargs)
        self._supports_ragged_inputs = True
        self.units = units
        self.input_dims = input_dims

    def build(self, input_shape):
        initializer = tf.keras.initializers.he_normal()
        self.w = self.add_weight(
            shape=(self.input_dims, self.units),
            initializer=initializer,
            trainable=True)
        
        self.b = self.add_weight(
            shape=(self.units,), 
            initializer=tf.zeros_initializer, 
            trainable=True)
        
    def call(self, inputs):
        return tf.ragged.map_flat_values(tf.matmul, inputs, self.w) + self.b

class Word_Matching_Network(tf.keras.Model):
    def __init__(self):
        super(Word_Matching_Network, self).__init__(name='Word_Matching_Network')
        self._supports_ragged_inputs = True        
        self.Layer1 = Dense(5, input_dims=30)
        self.Layer2 = Dense(5)
        self.Layer3 = Dense(1)

    def call(self, inputs):
        x = self.Layer1(inputs)
        x = tf.ragged.map_flat_values(tf.nn.relu, x)
        
        x = self.Layer2(x)
        x = tf.ragged.map_flat_values(tf.nn.relu, x)
        
        x = self.Layer3(x)
        x = tf.ragged.map_flat_values(tf.nn.relu, x)
        return x

class Gating_Network(tf.keras.layers.Layer):
    def __init__(self):
        super(Gating_Network, self).__init__()
        self._supports_ragged_inputs = True

    def build(self, input_shape):
        initializer = tf.keras.initializers.RandomUniform(minval=0, maxval=1)
        self.w = self.add_weight(
            shape=(1, 1),
            name='Gating_weight',
            initializer=initializer,
            trainable=True)

    def ragged_softmax(self, logits):
        numerator = tf.exp(logits)
        denominator = tf.reduce_sum(numerator, axis=1)
        softmax = tf.math.divide_no_nan(numerator, tf.reshape(denominator, shape=(logits.shape[0], -1)))
        return softmax
        
    def call(self, idf):
        g = tf.math.multiply(idf, self.w)
        softmax = self.ragged_softmax(g)
        return softmax
        
class Score_Aggregation(tf.keras.layers.Layer):
    def __init__(self):
        super(Score_Aggregation, self).__init__(name='Score_Aggregation')
        self._supports_ragged_inputs = True

    def call(self, Z, g):
        score = tf.ragged.map_flat_values(tf.reshape, Z, shape=(-1, ))
        gating = g
        s_g_sum = tf.math.multiply(gating, score)
        return tf.math.reduce_sum(s_g_sum, axis=1)


class Conv_stack(tf.keras.layers.Layer):
    def __init__(self, lg, nf):
        super(Conv_stack, self).__init__(name='ConV_stack')
        self.lg = lg
        self.nf = nf
        self.conv_dict = {}
        for i in range(2, self.lg+1):
            self.conv_dict[i] = tf.keras.layers.Conv2D(self.nf, i, strides=(1, 1), padding='same')

    def call(self, inputs):
        inputs = tf.expand_dims(inputs, axis=-1)
        x_1 = inputs
        x = {}
        for i in range(2, self.lg+1):
            x[i] = self.conv_dict[i](inputs)
        return tf.keras.layers.concatenate([x_1] + [x[k] for k in x]) 
        
class Dim_wise_max_pooling(tf.keras.layers.Layer):
    def __init__(self, lg, nf):
        super(Dim_wise_max_pooling, self).__init__(name='dim_wise_max_pooling')
        self.lg = lg
        self.nf = nf
        
    def call(self, inputs):
        channel_range = [self.nf*i+1 for i in range(self.lg)]
        x_1 = inputs[:, :, :, 0]
        x = {}
        for i in range(2, self.lg+1):
            x[i] = tf.reduce_max(inputs[:, :, :, channel_range[i-2]:channel_range[i-1]], axis=-1)
            
        return tf.keras.layers.concatenate([x_1] + [x[k] for k in x])
        
class Row_wise_max_pooling(tf.keras.layers.Layer):
    def __init__(self, ns, lg, firstk):
        super(Row_wise_max_pooling, self).__init__(name='row_wise_max_pooling')
        self.ns = ns
        self.lg = lg
        self.firstk = firstk
        
    def call(self, inputs):
        x = {}
        for i in range(1, self.lg+1):
            x[i] = tf.math.top_k(inputs[:, :, self.firstk*(i-1):self.firstk*i], k=self.ns)[0]
            
        return tf.keras.layers.concatenate([x[k] for k in x])
        
class Idf_concat(tf.keras.layers.Layer):
    def __init__(self):
        super(Idf_concat, self).__init__(name='idf_concat')
        
    def call(self, inputs, idf):
        expand_idf = tf.expand_dims(idf, axis=-1)
        return tf.keras.layers.concatenate([inputs, expand_idf])
        
class Recurrent_Layer(tf.keras.layers.Layer):
    def __init__(self, lq, ns, lg):
        super(Recurrent_Layer, self).__init__(name='Recurrent_Layer')
        self.inputs_shape = (lq, ns*lg+1)
        self.lstm = tf.keras.layers.LSTM(units=1, input_shape=self.inputs_shape)
        
    def call(self, inputs):
        return self.lstm(inputs)
        
        
        
        
        
        
        