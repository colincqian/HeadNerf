import torch
from headnerf_trainer import Trainer
from XGaze_utils.data_loader_xgaze import get_data_loader

import numpy as np

import configparser
import yaml
import argparse


class BaseOptions(object):
    def __init__(self, base_opt_dic,para_dict = None) -> None:
        super().__init__()
        for key in base_opt_dic:
            setattr(self, key, base_opt_dic[key])
        
        if para_dict is not None:
            self.featmap_size = para_dict["featmap_size"]
            self.featmap_nc = para_dict["featmap_nc"]
            self.pred_img_size = para_dict["pred_img_size"]

class Dict2Class(object):
    def __init__(self, my_dict):
        for key in my_dict:
            setattr(self, key, my_dict[key])
    
    def add(self,key,value):
        setattr(self,key,value)

def parse_argument():
    parser = argparse.ArgumentParser(description='Specifiy config file path')
    parser.add_argument('--config_file', type=str, default='config/train.yml',
                        help='Directory of the config file')
    args = parser.parse_args()
    return args


def load_config(config_file):
    with open(config_file,'r') as f:
        print(f'----Load Configuration from {config_file}----')
        config = yaml.load(f,Loader=yaml.FullLoader)
    
    config_dic = {}
    for k,v in config.items():
        if k in ['training_config','eval_config']:
            config_dic[k] = Dict2Class(v)
        if k in ["base_opt","dataset_config"]:
            config_dic[k] = v

    return config_dic

def run(training_config,dataset_config,base_opt):
    kwargs = {}

    if training_config.headnerf_options:
        check_dict = torch.load(training_config.headnerf_options, map_location=torch.device("cpu"))
        para_dict = check_dict["para"]
        opt = BaseOptions(base_opt,para_dict)
        dataset_config['opt'] =  opt

    if training_config.use_gpu:
        # ensure reproducibility
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.manual_seed(0)
        np.random.seed(0)
        kwargs = {'num_workers': training_config.num_workers}

    # instantiate data loaders
    if training_config.is_train:
        data_loader = get_data_loader(
                        mode='train',
                        batch_size=training_config.batch_size,
                        num_workers=training_config.num_workers,
                        dataset_config=dataset_config
                        )
    else:
        data_loader = get_data_loader(
                        mode='test',
                        batch_size=training_config.batch_size,
                        num_workers=training_config.num_workers,
                        dataset_config=dataset_config
                        )


    import cv2
    for data_info in data_loader[0]:
        temp_image = data_info['template_img']
        temp_image_np = (temp_image[0,0].detach().cpu().permute(1, 2, 0).numpy()* 255).astype(np.uint8)
        eye_mask = data_info['eye_mask']
        eye_mask_np = (eye_mask[0,0].detach().cpu().permute(1, 2, 0).numpy()).astype(np.uint8)
        head_mask = data_info['img_mask']
        head_mask_np = (head_mask[0,0].detach().cpu().permute(1, 2, 0).numpy()).astype(np.uint8)
        non_eye_mask = np.logical_xor(head_mask_np,eye_mask_np)
        cv2.imshow('current rendering', temp_image_np)
        cv2.waitKey(0) 
        #closing all open windows 
        cv2.destroyAllWindows() 
        cv2.imshow('current rendering', eye_mask_np)
        cv2.waitKey(0) 
        #closing all open windows 
        cv2.destroyAllWindows() 
        cv2.imshow('current rendering', head_mask_np)
        cv2.waitKey(0) 
        #closing all open windows 
        cv2.destroyAllWindows() 
        cv2.imshow('current rendering', non_eye_mask.astype(np.uint8)*255)
        cv2.waitKey(0) 
        #closing all open windows 
        cv2.destroyAllWindows() 

    # instantiate trainer
    training_config.add("base_opt",opt)
    trainer = Trainer(training_config, data_loader)

    # either train
    if training_config.is_train:
        trainer.train()
    # or load a pretrained model and test
    else:
        trainer.test()

if __name__ == '__main__':
    torch.manual_seed(0)
    args = parse_argument()
    config = load_config(args.config_file)
    run(**config)