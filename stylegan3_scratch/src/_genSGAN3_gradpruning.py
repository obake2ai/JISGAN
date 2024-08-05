import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import os.path as osp
import argparse
import numpy as np
from imageio import imsave

import torch

import dnnlib
import legacy
import moviepy.editor

import PIL
import cv2
from util.utilgan import latent_anima, basename, img_read
try: # progress bar for notebooks
    get_ipython().__class__.__name__
    from util.progress_bar import ProgressIPy as ProgressBar
except: # normal console
    from util.progress_bar import ProgressBar

import torch.nn.utils.prune as prune
from analyzeSounds import analyzeSong
import random

desc = "Customized StyleGAN2-ada on PyTorch"
parser = argparse.ArgumentParser(description=desc)
parser.add_argument('--out_dir', default='_out', help='output directory')
parser.add_argument('--model', default='models/ffhq-1024.pkl', help='path to pkl checkpoint file')
parser.add_argument('--labels', '-l', type=int, default=None, help='labels/categories for conditioning')
# custom
parser.add_argument('--size', default=None, help='output resolution, set in X-Y format')
parser.add_argument('--scale_type', default='pad', help="main types: pad, padside, symm, symmside")
parser.add_argument('--latmask', default=None, help='external mask file (or directory) for multi latent blending')
parser.add_argument('--nXY', '-n', default='1-1', help='multi latent frame split count by X (width) and Y (height)')
parser.add_argument('--splitfine', type=float, default=0, help='multi latent frame split edge sharpness (0 = smooth, higher => finer)')
parser.add_argument('--trunc', type=float, default=1.0, help='truncation psi 0..1 (lower = stable, higher = various)')
parser.add_argument('--digress', type=float, default=0, help='distortion technique by Aydao (strength of the effect)')
parser.add_argument('--save_lat', action='store_true', help='save latent vectors to file')
# parser.add_argument('--seed', type=int, default=None)
parser.add_argument('--verbose', '-v', action='store_true')
# animation
parser.add_argument('--frames', default='200-25', help='total frames to generate, length of interpolation step')
parser.add_argument("--cubic", action='store_true', help="use cubic splines for smoothing")
parser.add_argument("--gauss", action='store_true', help="use Gaussian smoothing")
parser.add_argument("--save_video", action='store_true', default=True, help="save video files from geenrated images")
parser.add_argument("--variations", type=int, default=1)
parser.add_argument("--noise_seed", type=int, default=696)
parser.add_argument('--cbase',        help='Capacity multiplier', metavar='INT',                      type=int, default=32768)
parser.add_argument('--cmax',         help='Max. feature maps', metavar='INT',                        type=int, default=512)
parser.add_argument('--batch',        help='Total batch size', metavar='INT',                         type=int, default=2)
parser.add_argument('--custom', action='store_true', default=True)
parser.add_argument("--prune", default=None, help="specify layers for pruning (1-14)")
parser.add_argument("--prune_val", type=float, default=None, help="specify a value for pruning (0.0-1.0)")
parser.add_argument("--song", type=str, default=None, help="specify song if you want")
parser.add_argument("--tempo", type=float, default=0.5, help="specify tempo if you want")
# image
parser.add_argument("--image", action='store_true', default=False)
parser.add_argument("--resize_fhd", action='store_true', default=False)

a = parser.parse_args()

if a.size is not None: a.size = [int(s) for s in a.size.split('-')][::-1]
[a.frames, a.fstep] = [int(s) for s in a.frames.split('-')]
if a.prune is not None:
  outprune = f'_grad{a.prune}_{a.prune_val}'
  a.prune = [f'L{int(s)}_' for s in a.prune.split('-')]

def generate_images(
    G,
    seed,
    truncation_psi=1.0,
    noise_mode='const',
    outdir='./out',
    translate='0,0',
    rotate=0.0,
    class_idx=None
):
    device = torch.device('cuda')
    # Labels.
    label = torch.zeros([1, G.c_dim], device=device)
    if G.c_dim != 0:
        if class_idx is None:
            # raise click.ClickException('Must specify class label with --class when using a conditional network')
          label[:, class_idx] = 1
    else:
        if class_idx is not None:
            print ('warn: --class=lbl ignored when running on an unconditional network')
    # Generate images.
    z = torch.from_numpy(np.random.RandomState(seed).randn(1, G.z_dim)).to(device)
    #z = torch.randn(1, G.z_dim, device=device)
    # Construct an inverse rotation/translation matrix and pass to the generator.  The
    # generator expects this matrix as an inverse to avoid potentially failing numerical
    # operations in the network.
    # if hasattr(G.synthesis, 'input'):
    #     m = make_transform(translate, rotate)
    #     m = np.linalg.inv(m)
    #     G.synthesis.input.transform.copy_(torch.from_numpy(m))

    img = G(z, label, truncation_psi=truncation_psi, noise_mode=noise_mode)
    img = (img.permute(0, 2, 3, 1) * 127.5 + 128).clamp(0, 255).to(torch.uint8)
    PIL.Image.fromarray(img[0].cpu().numpy(), 'RGB').save(f'{outdir}/seed{seed:04d}.png')



def get_noise_vectors(song, seed=None, tempo=0.5):
    import easydict
    args = easydict.EasyDict({
        'song': song,
        'resolution': 512,
        'duration' : None,
        'pitch_sensitivity': 200,
        'tempo_sensitivity': tempo,
        'depth': 1,
        'num_classes': 12,
        'sort_classes_by_power': 0,
        'jitter': 0.5,
        'frame_length': 512,
        'truncation': 1,
        'smooth_factor': 20,
        'batch_size': 30,
        'use_previous_classes': 0,
        'use_previous_vectors': 0,
        'output_path': '.',
        'first_vector': None,
        'noise_seed' : seed,
    })
    return analyzeSong(args)

# def prune_module(name, module, mount):
#     try:
#         prune.random_unstructured(module, name='weight', amount=mount)
#         #prune.ln_structured(module, name="weight", amount=mount)
#         #print('{} : {}% pruned'.format(name,mount*100))
#     except:
#         pass
#         #print('{} : skipped'.format(name))

# def prune_layer(Gs, layer_name, prune_mount):
#     for name, module in Gs.named_modules():
#         if layer_name in name: prune_module(name, module, prune_mount)
#     return Gs

def custom_prune_unstructured(module, name='weight', amount=0.5, seed=None):
    # シード値を固定
    torch.manual_seed(seed)

    # 重みを取得
    tensor = getattr(module, name)

    # 剪定する重みの数を計算
    total_params = tensor.nelement()
    prune_count = int(total_params * amount)

    # 重みの総数に基づいてランダムなインデックスを生成
    mask = torch.ones_like(tensor)
    flat_indices = torch.randperm(total_params)[:prune_count]
    mask.view(-1)[flat_indices] = 0

    # 重みを剪定
    tensor.data.mul_(mask)
    #print('pruned!')

def prune_module(name, module, mount, seed=None):
    try:
        custom_prune_unstructured(module, name='weight', amount=mount, seed=seed)
    except:
        pass

def prune_layer(Gs, layer_name, prune_mount, seed=None):
    for name, module in Gs.named_modules():
        if layer_name in name: prune_module(name, module, prune_mount, seed=seed)
    return Gs

device = torch.device('cuda')

# setup generator
Gs_kwargs = dnnlib.EasyDict()
Gs_kwargs.verbose = a.verbose
Gs_kwargs.size = a.size
Gs_kwargs.scale_type = a.scale_type

#!!! custom
Gs_kwargs.channel_base = a.cbase
Gs_kwargs.channel_max = a.cmax
# Gs_kwargs.mapping_kwargs.num_layers = (8 if opts.cfg == 'stylegan2' else 2) if opts.map_depth is None else opts.map_depth
# Gs_opt_kwargs.lr = (0.002 if opts.cfg == 'stylegan2' else 0.0025) if opts.glr is None else opts.glr
# Gs_kwargs.class_name = 'training.networks_stylegan3.Generator'
Gs_kwargs.magnitude_ema_beta = 0.5 ** (a.batch / (20 * 1e3))
Gs_kwargs.num_fp16_res = 0
Gs_kwargs.conv_clamp = None
Gs_kwargs.conv_kernel = 1 # Use 1x1 convolutions.
Gs_kwargs.channel_base *= 2 # Double the number of feature maps.
Gs_kwargs.channel_max *= 2
Gs_kwargs.use_radial_filters = True # Use radially symmetric downsampling filters.

pruned = False
total_prune = 0

def generate(Gs, noise_seed, val=1):
    # torch.manual_seed(a.noise_seed)
    # if torch.cuda.is_available():
    #     torch.cuda.manual_seed_all(a.noise_seed)
    # np.random.seed(a.noise_seed)
    # random.seed(a.noise_seed)
    # os.makedirs(a.out_dir, exist_ok=True)

    torch.manual_seed(noise_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(noise_seed)
    np.random.seed(noise_seed)
    random.seed(noise_seed)

    # mask/blend latents with external latmask or by splitting the frame
    if a.latmask is None:
        nHW = [int(s) for s in a.nXY.split('-')][::-1]
        assert len(nHW)==2, ' Wrong count nXY: %d (must be 2)' % len(nHW)
        n_mult = nHW[0] * nHW[1]
        if a.verbose is True and n_mult > 1: print(' Latent blending w/split frame %d x %d' % (nHW[1], nHW[0]))
        lmask = np.tile(np.asarray([[[[1]]]]), (1,n_mult,1,1))
        Gs_kwargs.countHW = nHW
        Gs_kwargs.splitfine = a.splitfine
    else:
        if a.verbose is True: print(' Latent blending with mask', a.latmask)
        n_mult = 2
        if osp.isfile(a.latmask): # single file
            lmask = np.asarray([[img_read(a.latmask)[:,:,0] / 255.]]) # [1,1,h,w]
        elif osp.isdir(a.latmask): # directory with frame sequence
            lmask = np.expand_dims(np.asarray([img_read(f)[:,:,0] / 255. for f in img_list(a.latmask)]), 1) # [n,1,h,w]
        else:
            print(' !! Blending mask not found:', a.latmask); exit(1)
        if a.verbose is True: print(' latmask shape', lmask.shape)
        lmask = np.concatenate((lmask, 1 - lmask), 1) # [frm,2,h,w]
    lmask = torch.from_numpy(lmask).to(device)

    if a.song is None:
        out_name = "%s_%s_%s_size%d-%d_n%s_splitfine%f_digress%f" \
                %(a.model.split("/")[len(a.model.split("/"))-2], a.model.split("/")[len(a.model.split("/"))-1].split(".")[0], str(noise_seed+val-1), a.size[0], a.size[1], a.nXY, a.splitfine, a.digress)
    else:
        model_name = os.path.basename(a.model).split(".")[0]
        song_name = os.path.basename(a.song).split(".")[0]
        tempo_name = str(a.tempo).replace(".","_")
        out_name = f"{model_name}_{noise_seed+val-1}_song{song_name}_tempo{tempo_name}"
    print(' .. Gs custom ..', basename(a.model))

    # load base or custom network

    if a.verbose is True: print(' out shape', Gs.output_shape[1:])

    if a.verbose is True: print(' making timeline..')
    lats = [] # list of [frm,1,512]
    for i in range(n_mult):
        lat_tmp = latent_anima((1, Gs.z_dim), a.frames, a.fstep, cubic=a.cubic, gauss=a.gauss, seed=noise_seed+val-1, verbose=False) # [frm,1,512]
        lats.append(lat_tmp) # list of [frm,1,512]
        #print ("lat_tmp", lat_tmp.shape)

    if a.song is not None:
        lats = []
        if a.verbose is True: print(' making songline..')
        for i in range(n_mult):
            noise_vectors, class_vectors = get_noise_vectors(song=a.song, seed=noise_seed+i, tempo=a.tempo)
            #print (noise_vectors.shape, 10+i)
            lat_tmp =np.array(noise_vectors[:, i, :][:,np.newaxis,:])
            #print ("audio lat_tmp", lat_tmp.shape)
            lats.append(lat_tmp)
        a.frames = int(noise_vectors.shape[0])/a.fstep
        out_name = out_name + "_%s_tempo%f"%(osp.basename(a.song).split(".")[0], a.tempo)

    latents = np.concatenate(lats, 1) # [frm,X,512]

    print(' latents', latents.shape)
    latents = torch.from_numpy(latents).to(device)
    frame_count = latents.shape[0]
    duration_sec = frame_count / 30

    # distort image by tweaking initial const layer
    if a.digress > 0:
        try: init_res = Gs.init_res
        except: init_res = (4,4) # default initial layer size
        dconst = []
        for i in range(n_mult):
            dc_tmp = a.digress * latent_anima([1, Gs.z_dim, *init_res], a.frames, a.fstep, cubic=True, seed=noise_seed, verbose=False)
            dconst.append(dc_tmp)
        dconst = np.concatenate(dconst, 1)
    else:
        dconst = np.zeros([frame_count, 1, 1, 1, 1])
    dconst = torch.from_numpy(dconst).to(device)

    # labels / conditions
    label_size = Gs.c_dim
    if label_size > 0:
        labels = torch.zeros((frame_count, n_mult, label_size), device=device) # [frm,X,lbl]
        if a.labels is None:
            label_ids = []
            for i in range(n_mult):
                label_ids.append(random.randint(0, label_size-1))
        else:
            label_ids = [int(x) for x in a.labels.split('-')]
            label_ids = label_ids[:n_mult] # ensure we have enough labels
        for i, l in enumerate(label_ids):
            labels[:,i,l] = 1
    else:
        labels = [None]


    if a.prune is not None:
        out_name+=outprune

    prune_step = a.prune_val/(frame_count-1)

    # 中間動画ファイルの保存先リスト
    intermediate_videos = []

    # 2000フレームごとに動画を保存するための関数
    def save_intermediate_video(start_frame, end_frame):
        def make_frame(t):
            global pruned, total_prune
            frame_idx = int(np.clip(np.round(t * 30), 0, frame_count - 1))
            latent  = latents[frame_idx]
            label   = labels[frame_idx % len(labels)]
            latmask = lmask[frame_idx % len(lmask)] if lmask is not None else [None]
            dc      = dconst[frame_idx % len(dconst)]

            if not pruned:
                total_prune += prune_step
                for name, module in Gs.named_modules():
                    for s in a.prune:
                        if s in name:
                            prune_module(name, module, total_prune, noise_seed)
                pruned = True

            if a.custom:
                images = Gs(latent, label, latmask, dc, truncation_psi=a.trunc, noise_mode='const')
            else:
                images = Gs(latent, label, truncation_psi=a.trunc, noise_mode='const')
            images = (images.permute(0,2,3,1) * 127.5 + 128).clamp(0, 255).to(torch.uint8).cpu().numpy()
            #print(total_prune)
            pruned = False
            if a.image == True:
              PIL.Image.fromarray(images[0], 'RGB').save(f'{a.out_dir}/seed{out_name}.png')
            if a.resize_fhd:
              resized_image = cv2.resize(images[0], (1920, 1080))
              return resized_image
            else:
              return images[0]

        out_name_temp = out_name + f"_part{start_frame}-{end_frame}"
        intermediate_path = osp.join(a.out_dir, f"{out_name_temp}.mp4")
        intermediate_videos.append(intermediate_path)

        moviepy.editor.VideoClip(make_frame, duration=(end_frame-start_frame)/30).write_videofile(intermediate_path, fps=30, codec='libx264', bitrate='16M')
        pkl_path = osp.join(a.out_dir, f"{out_name_temp}.pkl")
        with open(pkl_path, 'wb') as f:
            torch.save(Gs.state_dict(), f)
            
    # 2000フレームごとに動画を保存
    # for start_frame in range(0, frame_count, 2000):
    #     end_frame = min(start_frame + 2000, frame_count)
    #     save_intermediate_video(start_frame, end_frame)
    save_intermediate_video(0, frame_count)
    # すべての中間動画を結合
    clips = [moviepy.editor.VideoFileClip(video) for video in intermediate_videos]
    final_clip = moviepy.editor.concatenate_videoclips(clips)
    final_clip.write_videofile(osp.join(a.out_dir, f"{out_name}.mp4"), fps=30, codec='libx264', bitrate='16M')

    # 中間動画を削除
    for video in intermediate_videos:
        os.remove(video)

    # if a.image == True:
    #   make_frame(1)
    # else:
    #   moviepy.editor.VideoClip(make_frame, duration=duration_sec).write_videofile(osp.join(a.out_dir, "%s.mp4"%out_name), fps=30, codec='libx264', bitrate='16M')

    

    # convert latents to dlatents, save them
    if a.save_lat is True:
        latents = latents.squeeze(1) # [frm,512]
        dlatents = Gs.mapping(latents, label) # [frm,18,512]
        if a.size is None: a.size = ['']*2
        filename = '{}-{}-{}.npy'.format(basename(a.model), a.size[1], a.size[0])
        filename = osp.join(osp.dirname(a.out_dir), filename)
        dlatents = dlatents.cpu().numpy()
        np.save(filename, dlatents)
        print('saved dlatents', dlatents.shape, 'to', filename)


# if __name__ == '__main__':
    # for i in range(a.variations):
    #     pkl_name = osp.splitext(a.model)[0]
    #     with dnnlib.util.open_url(pkl_name + '.pkl') as f:
    #         #print(Gs_kwargs)
    #         Gs = legacy.load_network_pkl(f, custom=a.custom, **Gs_kwargs)['G_ema'].to(device) # type: ignore
    #     generate(Gs, a.noise_seed, val=i)
if __name__ == '__main__':
    # 途中からの再開機能
    pkl_name = osp.splitext(a.model)[0]
    start_variation = 0
    resume_file = osp.join(a.out_dir, "resume.txt")
    if os.path.exists(resume_file):
        with open(resume_file, 'r') as f:
            start_variation = int(f.read())

    for i in range(start_variation, a.variations):
        with dnnlib.util.open_url(pkl_name + '.pkl') as f:
            Gs = legacy.load_network_pkl(f, custom=a.custom, **Gs_kwargs)['G_ema'].to(device)
        generate(Gs, a.noise_seed, val=i)

        # 進行状況を保存
        with open(resume_file, 'w') as f:
            f.write(str(i+1))
