#!/usr/bin/env python

import time as t
import myutils
import DeepLearningTB.DBN as db
import numpy as np
import theano
import theano.tensor as T
from hmm import HMM,EmissionModel
import cPickle
import argparse
import os

def main():
    
    parser = argparse.ArgumentParser( description='Parameters Specification.')
    parser.add_argument("-v", help="Show output verbosity.", type=int)
    parser.add_argument("-l", help="Number of hidden layers.", type=str)
    parser.add_argument("-rbme", help="Number of pretrain epochs of RBM.", type=int)
    parser.add_argument("-grbme", help="Number of pretrain epochs GRBM.", type=int)
    parser.add_argument("-fte", help="Number of finetune epochs.", type=int)
    parser.add_argument("-tr", help="Number of training utterances to take.", type=int)
    parser.add_argument("-dev", help="Number development utterances to take.", type=int)
    parser.add_argument("-prfreq", help="Frequency of saving models in pretraining, in epochs.", type=int)
    parser.add_argument("-ftfreq", help="Frequency of saving models in finetuning, in epochs.", type=int)
    parser.add_argument("-ftonly", help="Finetune the model only followed by HMM training.", type=str)
    parser.add_argument("-hmmonly", help="Train HMM  model only.", type=str)
    parser.add_argument("-hmme", help="HMM training epochs.", type=int)
    parser.add_argument("-maxbatch", help="Max batch size.", type=int)
    parser.add_argument("-tin", help="Use tin's dataset.", type=int)

    args = parser.parse_args()
    
    ################################################
    ################# Model Parameters  ############
    ################################################
    
    core_test_set = ['mdab0','mwbt0','felc0',
                     'mtas1','mwew0','fpas0',
                     'mjmp0','mlnt0','fpkt0',
                     'mlll0','mtls0','fjlm0',
                     'mbpm0','mklt0','fnlp0',
                     'mcmj0','mjdh0','fmgd0',
                     'mgrt0','mnjm0','fdhc0',
                     'mjln0','mpam0','fmld0']




    #General
    n_phonemes = 61
    n_states_per_phoneme = 1
    utterances_tr = args.tr if args.tr is not None else None
    utterances_dev = args.dev if args.dev is not None else None
    pr_model_save_freq = args.prfreq if args.prfreq is not None else None
    ft_model_save_freq = args.ftfreq if args.ftfreq is not None else None
    ft_only_model = args.ftonly if args.ftonly is not None else None
    hmm_only_model  = args.hmmonly if args.hmmonly is not None else None
    max_batch = args.maxbatch if args.maxbatch is not None else 50000
    
    if args.tin:
        #Using Tin's experiments, no input extension
        extend_input_n=1
    else:
        #Consider a window of 11 frames as input
        extend_input_n = 11
    
    hmm_iters      = args.hmme if args.hmme is not None else np.inf
    
    
    ############################################
    ### DBN Params (pre-train and finetune) ####
    ############################################
    
    k=1                                         # CD_k, number of iterations
    n_ins   = 13*extend_input_n                 # number of inputs, 13 MFCC each frame  
    
    if args.l is not None :
        hidden_layers_sz = [int(i) for i in args.l.split(',')]
    else:
        hidden_layers_sz = [2048, 2048, 2048, 2048]
    
    

    pretraining_epochs = args.grbme #= args.e if args.e is not None else 225
    finetune_epochs    = args.fte if args.fte is not None else np.inf
    
    models_base_path = os.environ['MT_ROOT']+'/Models/'
    if args.tin:
        model_dir_path = models_base_path+str(len(hidden_layers_sz))+'x'+str(hidden_layers_sz[0])+'_pr_'+str(pretraining_epochs)+'_tin'+'/'
    else:
        model_dir_path = models_base_path+str(len(hidden_layers_sz))+'x'+str(hidden_layers_sz[0])+'_pr_'+str(pretraining_epochs)+'/'
    
    #Delete Previous Models
    if hmm_only_model is None and ft_only_model is None : 
        if not os.path.exists(model_dir_path):
            os.makedirs(model_dir_path)
        else:
            for f in os.listdir(model_dir_path):
                if not f.endswith('tin.save'):
                    os.remove(model_dir_path+f)
    
    #Params taken from George Dahl publication
    rbm_lr = 0.02
    grbm_lr = 0.002
    w_cost = 0.0002
    # fine-tune params
    finetune_lr = 0.1
    
    
    
    #########################
    ##### Fetching data #####
    #########################
    if args.tin:
        if args.v >= 1 : 
            print '... loading tins data.'

        stacked_features_tr,stacked_labels_tr,prior_tr,mean_tr,std_tr = myutils.read_tins_data(os.environ['TIMIT']+'/tin/',p = 0)
        
        mfcc_f_dev = myutils.read_dev_files(os.environ['TIMIT']+'/test',core_test_set,n_spk=50)
        stacked_features_dev,stacked_labels_dev,frame_idces_dev,prior_dev,_,_ = myutils.process_mfcc_files(mfcc_f_dev, n_phonemes, n=utterances_dev,mean=mean_tr,std=std_tr,n_states_per_phoneme=n_states_per_phoneme)




        #print prior_tr
    else:
        if args.v >= 1:
            t1 = t.time()
        #training
        mfcc_f_tr = myutils.read_mfcc_files(os.environ['TIMIT']+'/train')
        stacked_features_tr,stacked_labels_tr,frame_idces_tr,prior_tr,mean_tr,std_tr = myutils.process_mfcc_files(mfcc_f_tr,n_phonemes, n=utterances_tr, n_states_per_phoneme=n_states_per_phoneme)
    #print 'Num of phn: '+ str(len(prior_tr))
    #print np.matrix(prior_tr).shape
  

        core_test_set = ['mdab0','mwbt0','felc0',
                         'mtas1','mwew0','fpas0',
                         'mjmp0','mlnt0','fpkt0',
                         'mlll0','mtls0','fjlm0',
                         'mbpm0','mklt0','fnlp0',
                         'mcmj0','mjdh0','fmgd0',
                         'mgrt0','mnjm0','fdhc0',
                         'mjln0','mpam0','fmld0']
    
        #retreive 50 speakers excluding core_test_set
        mfcc_f_dev = myutils.read_dev_files(os.environ['TIMIT']+'/test',core_test_set,n_spk=50)
        stacked_features_dev,stacked_labels_dev,frame_idces_dev,prior_dev,_,_ = myutils.process_mfcc_files(mfcc_f_dev, n_phonemes, n=utterances_dev,mean=mean_tr,std=std_tr,n_states_per_phoneme=n_states_per_phoneme)
    
    
        #to make it dividable to batch size
        if args.tr is None and args.tin is None:
            stacked_features_tr = stacked_features_tr[0:-3,]
            stacked_labels_tr   = stacked_labels_tr[0:-3,]
            frame_idces_tr[-1,1] -= 3

          #Concatenate the input
        if args.tin is None:
            stacked_features_tr  = myutils.extend_input(stacked_features_tr, frame_idces_tr, extend_input_n)
            stacked_features_dev = myutils.extend_input(stacked_features_dev, frame_idces_dev, extend_input_n)

           
        if args.v >= 1 :
            t2 = t.time()
            print "Time Processing Files: "+str(t2-t1)
    
    #Building train, validation and test sets with respective batches
    
    batch_size_tr      = myutils.get_batch_size(stacked_features_tr.shape[0], max_batch)
    batch_size_dev     = myutils.get_batch_size(stacked_features_dev.shape[0], max_batch)
    
    n_train_batches    = stacked_features_tr.shape[0] / batch_size_tr
    n_dev_batches      = stacked_features_dev.shape[0] / batch_size_dev
    
    train_set_x = theano.shared(np.asarray(stacked_features_tr,dtype=theano.config.floatX),
                                name='training_set',borrow=True)
    train_set_y = theano.shared(np.asarray(stacked_labels_tr,dtype='int32'),
                                name='training_labels',borrow=True)
    
    dev_set_x = theano.shared(np.asarray(stacked_features_dev,dtype=theano.config.floatX),
                              name='test_set',borrow=True)
    
    dev_set_y = theano.shared(np.asarray(stacked_labels_dev,dtype='int32'),
                              name='test_labels',borrow=True)
    
    test_set_x = dev_set_x
    test_set_y = dev_set_y
    
    
    if args.tin is None:
        utterances_idces_tr = theano.shared(np.asarray(frame_idces_tr, dtype='int32'),
                                        name='train_idces', borrow=True)
    
        utterances_idces_dev = theano.shared(np.asarray(frame_idces_dev, dtype='int32'),
                                         name='test_idces', borrow=True)

    #Write mean_tr and std_tr
    
    f = file(model_dir_path+'mean_std_pr.save', 'wb')
    cPickle.dump([mean_tr,std_tr,prior_tr], f, protocol=cPickle.HIGHEST_PROTOCOL)
    f.close()
    
    
    ##############
    # Print Info #
    ##############
    if args.v >= 1 :
        print 'Model: '+str(len(hidden_layers_sz))+'x'+str(hidden_layers_sz[0])
        print '====Training===='
        if args.tin is None:
            print 'Total utterances: ' + str(frame_idces_tr.shape[0])
        print 'Total MFCCs: ' + str(stacked_features_tr.shape[0])
        print 'batch size: '+str(batch_size_tr)
        print 'number of batches: '+str(n_train_batches)
        
        print '====Validation===='
        if args.tin is None:
            print 'Total utterances: ' + str(frame_idces_dev.shape[0])
        print 'Total MFCCs: ' + str(stacked_features_dev.shape[0])
        print 'batch size: '+str(batch_size_dev)
        print 'number of batches: '+str(n_dev_batches)
    
        
    ##########################
    ###### DBN Pretrain ######
    ##########################
    if (ft_only_model is None and hmm_only_model is None):
        if args.v >= 1 :
            print '... building dbn model.'
    
        dbn = db.DBN(np.random.RandomState(123), theano_rng=None, n_ins=n_ins,
                         hidden_layers_sizes=hidden_layers_sz, n_outs=n_phonemes*n_states_per_phoneme)
            
        if args.v >= 1 :
            print '... getting the pretraining functions'
            start_time = t.time()
        
       # print train_set_x.get_value().shape
        pretraining_fns = dbn.pretraining_functions(train_set_x=train_set_x,
                                                    batch_size=batch_size_tr,
                                                    k=k,
                                                    weight_p = w_cost)
        if args.v >= 1 :
            end_time = t.time()
            print 'Getting pre-training function total time: ' + str(end_time - start_time)
            print '... pre-training dbn model.'
            start_time = t.time()
    
        ## Pre-train layer-wise
    
        for i in xrange(dbn.n_layers):
            # go through pretraining epochs
            pr_e = args.rbme if i>0 else args.grbme 
            for epoch in xrange(pr_e):
                # go through the training set
                c = []
            
                momentum = 0 if epoch == 0 else 0.9
                for batch_index in xrange(n_train_batches):
                    if i==0:
                        c.append(pretraining_fns[i](index=batch_index,
                                                    lr=grbm_lr,
                                                    momentum=momentum))
                    else:
                        c.append(pretraining_fns[i](index=batch_index,
                                                    lr=rbm_lr,
                                                    momentum=momentum))
                if args.v>=2:
                     print 'Pre-training layer %i, epoch %d, cost ' % (i, epoch),
                     print np.mean(c)
                   
                    
                if ( pr_model_save_freq is not None) and ((epoch+1)%pr_model_save_freq == 0) and (epoch != 0):
                    f_dbn = file(model_dir_path+'DBN_RBM_pr_'+str(epoch+1)+'_ft_0.save', 'wb')
                    cPickle.dump(dbn, f_dbn, protocol=cPickle.HIGHEST_PROTOCOL)
                    f_dbn.close()
    
        if args.v >= 1 :
            end_time = t.time()
            print '... pretraining total time: ' + str(end_time - start_time)



    #########################
    ###### Fine Tuning ######
    #########################
    if (hmm_only_model is None) :
        if (ft_only_model is not None):
            if args.v >= 1 :
                print '... loading pickled dbn.'
            f_dbn = file(model_dir_path+ft_only_model, 'rb')
            dbn = cPickle.load(f_dbn)
            f_dbn.close()

        datasets = []
        datasets.append((train_set_x, train_set_y))
        datasets.append((dev_set_x, dev_set_y))
        datasets.append((test_set_x, test_set_y))
    
        if args.v >= 1 :
            print '... getting fine-tune functions.'
            start_time = t.time()
    
    
        train_fn, validate_model, test_model = dbn.build_finetune_functions(datasets=datasets, 
                                                                            batch_size_tr=batch_size_tr,
                                                                            batch_size_tst=batch_size_dev,
                                                                            batch_size_dev=batch_size_dev,
                                                                            weight_penalty = w_cost)
        if args.v >= 1 :
            end_time = t.time()
            print '... new method of Fine-Tune !'
            print '... fine-tune functions total time: ' + str(end_time - start_time)
            print '... fine-tuning the model.'
            start_time = t.time()

    #done_looping = False
    
        best_params = None
        best_validation_loss = np.inf
        last_validation_loss = np.inf
        test_score = 0.
        epoch = 0
        patience = 50
    
        while (finetune_lr > 0.001) and (epoch < finetune_epochs):
            epoch = epoch + 1
            momentum = 0 if epoch == 1 else 0.9
            dbn.save_last_params()
            for minibatch_index in xrange(n_train_batches):

                minibatch_avg_cost = train_fn(minibatch_index,lr=finetune_lr,momentum=momentum)
                iter = (epoch - 1) * n_train_batches + minibatch_index
                #if args.v >= 2 :
                 #   print('epoch %i, minibatch %i/%i, training log error %f ' % \
                  #            (epoch, minibatch_index + 1, n_train_batches,
                   #            np.array(minibatch_avg_cost)))

            
            # Save model if meeting freq of saving
            if (ft_model_save_freq is not None) and (epoch%ft_model_save_freq == 0):
                f_dbn = file(model_dir_path+'DBN_RBM_pr_'+str(pretraining_epochs)+'_ft_'+str(epoch)+'.save', 'wb')
                cPickle.dump(dbn, f_dbn, protocol=cPickle.HIGHEST_PROTOCOL)
                f_dbn.close()        
        
            validation_losses = validate_model()
            this_validation_loss = np.mean(validation_losses)
            if args.v >= 2 :
                print('epoch %i, validation error %f %%' % \
                          (epoch, this_validation_loss*100.))
            
            if this_validation_loss < best_validation_loss:
                best_validation_loss = this_validation_loss
                dbn.save_best_params()
                
            if this_validation_loss > last_validation_loss:
                #dbn.save_params()
                #best_validation_loss = this_validation_loss
                #patience = 51
                dbn.load_last_params()
                finetune_lr*=0.5
                
            
                #patience-=1      
            last_validation_loss=this_validation_loss
            
            
        dbn.load_best_params()
        if args.v >= 1 :
            end_time   = t.time()
            print '... fine-tuning total time: ' + str(end_time - start_time)
        # Pickling DBN-DNN
        f_dbn = file(model_dir_path+'DBN_RBM_final.save', 'wb')
        cPickle.dump(dbn, f_dbn, protocol=cPickle.HIGHEST_PROTOCOL)
        f_dbn.close()
    



    ####################
    ### Building HMM ###
    ####################
    if args.tin is None:
        if (hmm_only_model is not None):
            if args.v >= 1 :
                print '... loading pickled dbn.'
        
            f_dbn = file(model_dir_path+'DBN_RBM_final.save', 'rb')
            dbn = cPickle.load(f_dbn)
            f_dbn.close()
        
            if args.v >= 1 :
                print '... loading pickled HMM model.'
            f_hmm = file(model_dir_path+hmm_only_model, 'rb')
            pi,A = cPickle.load(f_hmm)
            f_hmm.close()

        else:    
            if args.v >= 1 :
                print '... initializing HMM.'
            pi,A = myutils.build_initial_hmm_mat(n_states_per_phoneme, n_phonemes)
           # print pi
            #print A

            if args.v >= 1 :
                print '... building HMM.'
    #print A
            hmm = HMM(initial=pi, transition=A, emission=dbn, phoneme_priors=prior_tr) 
                
            train_fn,update_fn = hmm.build_train_fn(train_set_x, utterances_idces_tr)
            viterbi_fn = hmm.build_viterbi_fn(dev_set_x, utterances_idces_dev)
      
            if args.v >= 1 :
                print '... training HMM.'
                start_time = t.time()
  
            last_dev_logp = -np.inf
            
            
            ##Train HMM
            
            loop = True
            iters = 0
            while loop and  iters<hmm_iters:
                res = []
                for utterance_idx in xrange( utterances_idces_tr.get_value(borrow=True).shape[0]):
                    res.append(train_fn(utterance_idx) )
                
                print 'Training logp: %0.5f ' % (np.mean(res))
                #print hmm.A.get_value()
                update_fn()
                #print '=========U============='
                #print np.sum(hmm.A.get_value())
                #print hmm.A.get_value()

                #Compute dev per
                
                sols = [viterbi_fn(i)[0] for i in xrange( utterances_idces_dev.get_value().shape[0] )]
                logs = [viterbi_fn(i)[1] for i in xrange( utterances_idces_dev.get_value().shape[0] )]
                dev_logp = np.mean(logs)
                print 'Dev logp: %0.5f ' % (dev_logp)
                per = myutils.compute_per(sols, stacked_labels_dev, frame_idces_dev)
                
                #print "Mean dev last per: %0.5f" %(last_per)
                print "Mean dev per: %0.5f" %(per)


                #log_p_dev = []
                #for utterance_idx in xrange( utterances_idces_dev.get_value(borrow=True).shape[0]):
                #    log_p_dev.append(viterbi_fn(utterance_idx)[1])
                    #print res[2]
                    
                #log_p=np.mean(log_p_dev)
                #print last_log_p
                #print log_p

          
                if (dev_logp - last_dev_logp < 0.5) :
                    loop=False
                    #rewind params
                    #hmm.load_last_A()
                    
                #else:
                 #   hmm.save_last_A()
                last_dev_logp = dev_logp
                    
                #print hmm.gamma_hist.get_value()
                hmm.reset_historial()
                iters += 1
  
                if args.v >= 1 :
                    end_time = t.time()
                print '... HMM training time: ' + str(end_time - start_time)
  
  
   
    # Pickling HMM params (failing to load all model with dbn...) 
    
                if args.v >= 1 :
                    print '... saving HMM.'
       
                f_hmm = file(model_dir_path+'HMM_final.save', 'wb')
                cPickle.dump([hmm.pi.get_value(), hmm.A.get_value()], f_hmm, protocol=cPickle.HIGHEST_PROTOCOL)
                f_hmm.close()
#    
#    
#   
#   
   #print "DNN output "
   ##print res[4].shape
   #print res[4]
   #print np.array(hmm.pi.eval())
   #print np.array(hmm.A.eval())
   #
   #print "logp:"
   #print p1[0]
   #print "path:"
   #print p1[1]/3
   #print "trellis:"
   #print p1[2]
   ##print p2[0][0]
   #
   


if __name__ == "__main__":
    main()
