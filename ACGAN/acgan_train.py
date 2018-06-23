from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import sys
import time

import acgan_model as acgan

sys.path.append('../')
import image_utils as iu
from datasets import DataIterator
from datasets import CiFarDataSet as DataSet


results = {
    'output': './gen_img/',
    'model': './model/ACGAN-model.ckpt'
}

train_step = {
    'batch_size': 100,
    'global_step': 50001,
    'logging_interval': 500,
}


def main():
    start_time = time.time()  # Clocking start

    # Loading Cifar-10 DataSet
    ds = DataSet(height=32,
                 width=32,
                 channel=3,
                 ds_path="D:/DataSet/cifar/cifar-10-batches-py/",
                 ds_name='cifar-10')
    ds_iter = DataIterator(x=iu.transform(ds.train_images, '127'),
                           y=ds.train_labels,
                           batch_size=train_step['batch_size'],
                           label_off=False)  # using label # maybe someday, i'll change this param's name

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # ACGAN Model
        model = acgan.ACGAN(s, batch_size=train_step['batch_size'])

        # Initializing
        s.run(tf.global_variables_initializer())

        sample_y = np.zeros(shape=[model.sample_num, model.n_classes])
        for i in range(10):
            sample_y[10 * i:10 * (i + 1), i] = 1

        d_loss = 0.
        d_overpowered = False
        for global_step in range(train_step['global_step']):
            for batch_x, batch_y in ds_iter.iterate():
                batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                # Update D network
                if not d_overpowered:
                    _, d_loss = s.run([model.d_op, model.d_loss],
                                      feed_dict={
                                          model.x: batch_x,
                                          model.y: batch_y,
                                          model.z: batch_z,
                                      })

                # Update G/C network
                _, g_loss, _, c_loss = s.run([model.g_op, model.g_loss, model.c_op, model.c_loss],
                                             feed_dict={
                                                 model.x: batch_x,
                                                 model.y: batch_y,
                                                 model.z: batch_z,
                                             })

                d_overpowered = d_loss < g_loss / 3.

                if global_step % train_step['logging_interval'] == 0:
                    batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                    d_loss, g_loss, c_loss, summary = s.run([model.d_loss, model.g_loss, model.c_loss, model.merged],
                                                            feed_dict={
                                                                model.x: batch_x,
                                                                model.y: batch_y,
                                                                model.z: batch_z,
                                                            })

                    # Print loss
                    print("[+] Step %08d => " % global_step,
                          " D loss : {:.8f}".format(d_loss),
                          " G loss : {:.8f}".format(g_loss),
                          " C loss : {:.8f}".format(c_loss))

                    # Training G model with sample image and noise
                    sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim]).astype(np.float32)
                    samples = s.run(model.g_test,
                                    feed_dict={
                                        model.y: sample_y,
                                        model.z: sample_z,
                                    })

                    # Summary saver
                    model.writer.add_summary(summary, global_step)

                    # Export image generated by model G
                    sample_image_height = model.sample_size
                    sample_image_width = model.sample_size
                    sample_dir = results['output'] + 'train_{:08d}.png'.format(global_step)

                    # Generated image save
                    iu.save_images(samples,
                                   size=[sample_image_height, sample_image_width],
                                   image_path=sample_dir,
                                   inv_type='127')

                    # Model save
                    model.saver.save(s, results['model'], global_step)

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()
