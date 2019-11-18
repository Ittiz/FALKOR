from code.datasets import ChartImageDataset, DFDataset
from code.data_processing import add_ti, candles_to_inputs_and_labels
from code.models import CNN, RNN, load_model, save_model

from torch.utils.data import DataLoader, Dataset

import warnings
import torch
import os
import shutil
import pandas as pd
import numpy as np
import time


torch.backends.cudnn.benchmark = True

# Parameters
params = {'batch_size': 1,
          'shuffle': True,
          'num_workers': 1}

def _train(train_dl, model, optim, error_func, debug=False):
    losses = []
    for batch, labels in train_dl:
        if torch.cuda.is_available():    
            batch, labels = batch.cuda().float(), labels.cuda().float()
        else:
            batch, labels = batch.float(), labels.float()
        
        if debug: print("batch[0] __str__: {} labels[0] __str__: {}".format(batch[0], labels[0]))
        # set model to train mode
        model.train()
        
        # clear gradients
        model.zero_grad()
        
        output = model(batch)
        if debug: print("OUTPUT: shape: {} __str__ {}".format(output.shape, output))

        loss = error_func(output, labels)
        if debug: print("LOSS: {}".format(loss.item()))

        loss.backward()
        optim.step()
        
        losses.append(loss)

    return round(float(sum(losses))/len(losses), 6)

def _valid(valid_dl, model, optim, error_func):
    with torch.set_grad_enabled(False):
        losses = []

        for batch, labels in valid_dl:
            if torch.cuda.is_available(): 
                batch, labels = batch.cuda().float(), labels.cuda().float()
            else:
                batch, labels = batch.float(), labels.float()
            
            # set to eval mode
            model.eval()
            
            # clear gradients
            model.zero_grad()

            output = model(batch)
            loss = error_func(output, labels)

            losses.append(loss)
        
    return round(float(sum(losses) / len(losses)), 6)

def _test(test_dl, model, optim, error_func):
    with torch.set_grad_enabled(False):
        losses = []

        for batch, labels in test_dl:
            if torch.cuda.is_available(): 
                batch, labels = batch.cuda().float(), labels.cuda().float()
            else:
                batch, labels = batch.float(), labels.float()
            
            # set to eval mode
            model.eval()
            
            # clear gradients
            model.zero_grad()

            output = model(batch)
            loss = error_func(output, labels)

            losses.append(loss)
        
    return round(float(sum(losses) / len(losses)), 6)

def RMSE(x, y):
            
            #TODO automate this without model_name
            # have to squish x into a rank 1 tensor with batch_size length with the outputs we want
            if len(list(x.size())) == 2:
                 # torch.Size([64, 1])
                x = x.squeeze(1)
            elif len(list(x.size())) == 3:
                # torch.Size([64, 30, 1])
                x = x[:, 29, :] # take only the last prediction from the 30 time periods in our matrix
                x = x.squeeze(1)
    
            mse = torch.nn.MSELoss()
            return torch.sqrt(mse(x, y))

def train(model, optim, error_func, num_epochs, train_dl, valid_dl, test_dl=None, debug=False):
    """Train a PyTorch model with optim as optimizer strategy"""
    
    for epoch_i in range(num_epochs):     
        # forward and backward passes of all batches inside train_gen
        train_loss = _train(train_dl, model, optim, error_func, debug)
        valid_loss = _valid(valid_dl, model, optim, error_func)
        
        # run on test set if provided
        if test_dl is not None: test_output = _test(test_dl, model, optim, error_func)
        else: test_output = "no test selected"
        print("train loss: {}, valid loss: {}, test output: {}".format(train_loss, valid_loss, test_output))

def train_on_df(model, candles_df, lr, num_epochs, model_type, debug):
    torch.backends.cudnn.benchmark = True
    
    candles_df = add_ti(candles_df)
    
    inputs, labels = candles_to_inputs_and_labels(candles_df)

    # calculate s - index of train/valid split
    s = int(len(inputs) * 0.7)

    if model_type == 'CNN':
        train_ds = ChartImageDataset(inputs[:s], labels[:s])
        valid_ds = ChartImageDataset(inputs[s:], labels[s:])
    elif model_type =='RNN':
        train_ds = DFDataset(inputs[:s], labels[:s])
        valid_ds = DFDataset(inputs[s:], labels[s:])
   
    train_dl = DataLoader(train_ds, drop_last=True, **params)
    valid_dl = DataLoader(valid_ds, drop_last=True, **params)

    optim = torch.optim.Adam(model.parameters(), lr)
    
    train(model=model, optim=optim, error_func=RMSE, num_epochs=num_epochs, train_dl=train_dl, valid_dl=valid_dl, debug=debug)

def train_rnn(candles, file_name, lr, num_epochs, debug):
    if torch.cuda.is_available():
        model = RNN(11, 30, params['batch_size'], 100, 3).cuda()
    else:
        model = RNN(11, 30, params['batch_size'], 100, 3)
    load_model(model, file_name)
    train_on_df(model, candles, lr, num_epochs, 'RNN', debug=debug)
    save_model(model, file_name)

def train_cnn(candles, file_name, lr, num_epochs, debug):
    model = (CNN().cuda() if torch.cuda.is_available() else CNN())
    load_model(model, file_name)
    train_on_df(model, candles, lr, num_epochs, 'CNN', debug=debug)
    save_model(model, file_name)

def split_df(dfm, chunk_size):
    """Split a dataframe into chunk_size smaller chunks"""
    def index_marks(nrows, chunk_size):
        return range(1 * chunk_size, (nrows // chunk_size) * chunk_size, chunk_size)
    indices = index_marks(dfm.shape[0], chunk_size)
    return np.split(dfm, indices)

if __name__ == '__main__':
    models = ['RNN', 'CNN']
    model = input("Select model to train from {} (default: CNN): ".format(models)) or 'CNN'
    datapath = input("Please input path to OCHLV .csv file (default: tests/600_candles.csv): ") or 'tests/600_candles.csv'
    num_chunks = int(input("Chunk size for training. Max is num_rows(dataframe) (default: 120): ") or 120) 
    outputpath = input("Please input path to save and/or load models into/from (default: ./output): ") or './output'
    lr = float(input("Learning rate (default: 0.001): ") or 0.001)
    epochs = int(input("Epochs (default: 5): ") or 5) 
    debug = False
    
    candles_big = pd.read_csv(datapath)
    chunks = split_df(candles_big, num_chunks)
    start_chunk = int(input("Select chunk to start training from (starting from 0 to {}) (default: 0): ".format(len(chunks)-1)) or 0)
    
    for i, candles_chunk in enumerate(chunks):
        if i < start_chunk: 
            continue
        print("{}/{}".format(i, len(chunks)-1))
        if model == 'RNN':
            train_rnn(candles_chunk, outputpath, lr, epochs, debug)
        elif model == 'CNN':
            train_cnn(candles_chunk, outputpath, lr, epochs, debug)
