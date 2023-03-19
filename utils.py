import logging
import os
from io import BytesIO
from json import loads
import av
import pilk
from torch import load, FloatTensor
from numpy import float32
import librosa


class HParams():
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if type(v) == dict:
                v = HParams(**v)
            self[k] = v

    def keys(self):
        return self.__dict__.keys()

    def items(self):
        return self.__dict__.items()

    def values(self):
        return self.__dict__.values()

    def __len__(self):
        return len(self.__dict__)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __contains__(self, key):
        return key in self.__dict__

    def __repr__(self):
        return self.__dict__.__repr__()


def load_checkpoint(checkpoint_path, model):
    checkpoint_dict = load(checkpoint_path, map_location='cpu')
    iteration = checkpoint_dict['iteration']
    saved_state_dict = checkpoint_dict['model']
    if hasattr(model, 'module'):
        state_dict = model.module.state_dict()
    else:
        state_dict = model.state_dict()
    new_state_dict = {}
    for k, v in state_dict.items():
        try:
            new_state_dict[k] = saved_state_dict[k]
        except:
            logging.info("%s is not in the checkpoint" % k)
            new_state_dict[k] = v
    if hasattr(model, 'module'):
        model.module.load_state_dict(new_state_dict)
    else:
        model.load_state_dict(new_state_dict)
    logging.info("Loaded checkpoint '{}' (iteration {})".format(
        checkpoint_path, iteration))
    return


def get_hparams_from_file(config_path):
    with open(config_path, "r") as f:
        data = f.read()
    config = loads(data)

    hparams = HParams(**config)
    return hparams


def load_audio_to_torch(full_path, target_sampling_rate):
    audio, sampling_rate = librosa.load(full_path, sr=target_sampling_rate, mono=True)
    return FloatTensor(audio.astype(float32))


def wav2ogg(input, output):
    with av.open(input, 'rb') as i:
        with av.open(output, 'wb', format='ogg') as o:
            out_stream = o.add_stream('libvorbis')
            for frame in i.decode(audio=0):
                for p in out_stream.encode(frame):
                    o.mux(p)

            for p in out_stream.encode(None):
                o.mux(p)


# def wav2silk(input, output):
#     with av.open(input) as in_wav:
#         in_stream = in_wav.streams.audio[0]
#         sample_rate = in_stream.codec_context.sample_rate
#         with BytesIO() as pcm:
#             with av.open(pcm, 'w', 's16le') as out_pcm:
#                 out_stream = out_pcm.add_stream(
#                     'pcm_s16le',
#                     rate=sample_rate,
#                     layout='mono'
#                 )
#                 for frame in in_wav.decode(in_stream):
#                     frame.pts = None
#                     for packet in out_stream.encode(frame):
#                         out_pcm.mux(packet)
#
#             pilk.encode(out_pcm, output, pcm_rate=sample_rate, tencent=True)


def to_pcm(in_path: str) -> tuple[str, int]:
    out_path = os.path.splitext(in_path)[0] + '.pcm'
    with av.open(in_path) as in_container:
        in_stream = in_container.streams.audio[0]
        sample_rate = in_stream.codec_context.sample_rate
        with av.open(out_path, 'w', 's16le') as out_container:
            out_stream = out_container.add_stream(
                'pcm_s16le',
                rate=sample_rate,
                layout='mono'
            )
            try:
               for frame in in_container.decode(in_stream):
                  frame.pts = None
                  for packet in out_stream.encode(frame):
                     out_container.mux(packet)
            except:
               pass
    return out_path, sample_rate


def convert_to_silk(media_path: str) -> str:
    pcm_path, sample_rate = to_pcm(media_path)
    silk_path = os.path.splitext(pcm_path)[0] + '.silk'
    pilk.encode(pcm_path, silk_path, pcm_rate=sample_rate, tencent=True)
    os.remove(pcm_path)
    return silk_path