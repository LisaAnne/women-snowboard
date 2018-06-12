"""
Common code shared across data analysis scripts. Please run me in python 2.
"""
import os
import json, pickle, collections
import nltk
from bias_detection import create_dict_from_list # TODO consolidate nicely

class AnalysisBaseClass:

    """
    Each AnalysisBaseClass instance contains a set
    of captions on which inference is performed. All
    analysis methods that work at on a single caption
    path are stored as static methods, shared by all
    instances.
    """

    def __init__(self, caption_paths):
        """
        caption_paths -- paths to captions that need to be analyzed
        """
        self.caption_paths = caption_paths
    
    def accuracy(self, filter_imgs=None):
        """
        Print accuracy breakdown for all caption paths. 
        """
        for caption_path in caption_paths:
            print("Model name: %s" %caption_path[0])
            predictions = json.load(open(caption_path[1]))
            AnalysisBaseClass.accuracy_per_model(predictions,
                AnalysisBaseClass.man_word_list_synonyms,
                AnalysisBaseClass.woman_word_list_synonyms,
                filter_imgs,
                AnalysisBaseClass.img_2_anno_dict_simple)
   
    def retrieve_accuracy_with_confidence(self, filter_imgs=None):
        """
        Print the recall for the correct label over different
        levels of confidence for all caption paths.

        The correct label for a caption
        is the gender annotation when the number of ground
        truth captions is greater than the confidence threshold
        and a gender neutral word otherwise.
        """
        for caption_path in caption_paths:
            for confidence in range(1,6):
                print("Model name: %s, Confidence Level: %d" %(caption_path[0], confidence))
                predictions = json.load(open(caption_path[1]))
                AnalysisBaseClass.retrieve_accuracy_with_confidence_per_model(predictions,
                    confidence,
                    AnalysisBaseClass.man_word_list_synonyms,
                    AnalysisBaseClass.woman_word_list_synonyms,
                    filter_imgs=filter_imgs)

    ###############################################
    ###  Helpers (metrics over predicted set)  ####
    ###############################################

    @staticmethod
    def accuracy_per_model(predicted, man_word_list=['man'], woman_word_list=['woman'], filter_imgs=None, img_2_anno_dict_simple=None):
        """
        Prints accuracy of predictions.
        
        Args:
            predicted: list of dictionaries keyed by 'image_id' and 'caption'.
                predicted[i]['image_id'] is integer.
            X_word_list: list of synonyms used in computing accuracy of gender X
            filter_imgs: list of images (as integer id) to include in calculation.
                if None, include all of predicted.

        Returns: dictionary of images organized by gt x pred label
        """

        f_tp = 0.
        f_fp = 0.
        f_tn = 0.
        f_other = 0.
        f_total = 0.
        
        
        m_tp = 0.
        m_fp = 0.
        m_tn = 0.
        m_other = 0.
        m_total = 0.
        
        male_pred_female = []
        female_pred_male = []
        male_pred_male = []
        female_pred_female = []
        male_pred_other = []
        female_pred_other = []
        
        for prediction in predicted:
            image_id = prediction['image_id']
            if filter_imgs:
                if image_id not in filter_imgs:
                    continue
            male = img_2_anno_dict_simple[image_id]['male']
            female = img_2_anno_dict_simple[image_id]['female']
            sentence_words = nltk.word_tokenize(prediction['caption'].lower())
            pred_male = AnalysisBaseClass.is_gendered(sentence_words, 'man', man_word_list, woman_word_list)
            pred_female = AnalysisBaseClass.is_gendered(sentence_words, 'woman', man_word_list, woman_word_list)

            if (female & pred_female):
                f_tp += 1
                female_pred_female.append(prediction)
            if (male & pred_male):
                m_tp += 1
                male_pred_male.append(prediction)
            if (male & pred_female):
                f_fp += 1
                male_pred_female.append(prediction)
            if (female & pred_male):
                m_fp += 1
                female_pred_male.append(prediction)
            if ((not female) & (not pred_female)):
                f_tn += 1
            if ((not male) & (not pred_male)):
                m_tn += 1
            pred_other = (not pred_male) & (not pred_female)
            if (female & pred_other):
                f_other += 1
                female_pred_other.append(prediction)
            if (male & pred_other):
                m_other += 1
                male_pred_other.append(prediction)
            if female:
                f_total += 1
            if male:
                m_total += 1

        print "Of female images:"
        print "Man predicted %f percent." %(m_fp/f_total)
        print "Woman predicted %f percent." %(f_tp/f_total)
        print "Other predicted %f percent." %(f_other/f_total)
        print "%f	%f	%f" % (m_fp/f_total, f_tp/f_total, f_other/f_total)
        
        print "Of male images:"
        print "Man predicted %f percent." %(m_tp/m_total)
        print "Woman predicted %f percent." %(f_fp/m_total)
        print "Other predicted %f percent." %(m_other/m_total)
        print "%f	%f	%f"% (m_tp/m_total, f_fp/m_total, m_other/m_total)

        print "Of total:"
        print "Correct %f percent." %((m_tp+f_tp)/(m_total+f_total))
        print "Incorect %f percent." %((m_fp+f_fp)/(m_total+f_total))
        print "Other predicted %f percent." %((f_other+m_other)/(m_total+f_total))
        print "%f	%f	%f"% ((m_tp+f_tp)/(m_total+f_total), (m_fp+f_fp)/(m_total+f_total), (m_other+f_other)/(f_total+m_total))

        print "ratio", float(f_tp + f_fp)/(m_tp + m_fp)
        pred_images = {}
        pred_images['male_pred_male'] = male_pred_male
        pred_images['female_pred_female'] = female_pred_female
        pred_images['female_pred_male'] = female_pred_male
        pred_images['male_pred_female'] = male_pred_female
        pred_images['male_pred_other'] = male_pred_other
        pred_images['female_pred_other'] = female_pred_other
        
        return pred_images

    @staticmethod
    def retrieve_accuracy_with_confidence_per_model(predicted, confidence_threshold, man_word_list=['man'], woman_word_list=['woman'], filter_imgs=None):
        correct = 0
        incorrect = 0
        correct_m, correct_f = 0, 0
        incorrect_m, incorrect_f = 0, 0
        pred_m, pred_f = 0, 0
        not_m, not_f = 0, 0
        pred_m_not_m, pred_f_not_f = 0, 0

        bias_ids = list(AnalysisBaseClass.img_2_anno_dict_simple.keys()) # TODO: all predicted should be in this dictionary?
        for prediction in predicted:
            image_id = prediction['image_id']

            # TODO: consolidate conditions
            if filter_imgs:
                if image_id not in filter_imgs:
                    continue
            
            if image_id in bias_ids:
                is_male = AnalysisBaseClass.img_2_anno_dict_simple[image_id]['male']
                is_female = AnalysisBaseClass.img_2_anno_dict_simple[image_id]['female']
                gt_captions = AnalysisBaseClass.gt_caps[image_id]

                if is_male:
                    gender = 'man'
                else:
                    gender = 'woman'

                is_conf = AnalysisBaseClass.confidence_level(gt_captions, gender) >= confidence_threshold

                sentence_words = nltk.word_tokenize(prediction['caption'].lower())
                pred_male = AnalysisBaseClass.is_gendered(sentence_words, 'man', man_word_list, woman_word_list)
                pred_female = AnalysisBaseClass.is_gendered(sentence_words, 'woman', man_word_list, woman_word_list)

                if pred_male:
                    pred_m += 1

                if pred_female:
                    pred_f += 1

                # TODO: simplify logic
                if is_conf:
                    if is_female:
                        not_m += 1
                    if is_male:
                        not_f += 1
                    if (is_female & pred_female):
                        correct += 1
                        correct_f += 1
                    elif (is_male & pred_male):
                        correct += 1
                        correct_m += 1
                    else:
                        if is_female:
                            incorrect_f += 1
                            if pred_male:
                                pred_m_not_m += 1
                        else:
                            incorrect_m += 1
                            if pred_female:
                                pred_f_not_f += 1
                        incorrect += 1
                else:
                    not_m += 1
                    not_f += 1
                    pred_other = (not pred_male) & (not pred_female)
                    if pred_other:
                        correct += 1
                        if is_female:
                            correct_f += 1
                        else:
                            correct_m += 1
                    else:
                        if pred_male:
                            pred_m_not_m += 1
                        else:
                            pred_f_not_f += 1
                        if is_female:
                            incorrect_f += 1 
                        else:
                            incorrect_m += 1 
                        incorrect += 1

        male_tpr = correct_m / float(pred_m)
        male_fpr = pred_m_not_m / float(not_m)
        female_tpr = correct_f / float(pred_f)
        female_fpr = pred_f_not_f / float(not_f)

        print("Accuracy for Women: %f" % (correct_f / float(correct_f + incorrect_f)))
        print("Accuracy for Men: %f" % (correct_m / float(correct_m + incorrect_m)))
        print("Accuracy: %f" % (correct / float(correct + incorrect)))

        print("Men TPR / FPR: %f	%f" % (male_tpr, male_fpr)) 

        print("Women TPR / FPR: %f	%f" % (female_tpr, female_fpr)) 


    
    ###############################################
    ########             Utils             ########
    ###############################################

    @staticmethod
    def confidence_level(caption_list, gender):
        """Returns number of captions that say correct gender."""
        conf = 0
        for cap in caption_list:
            if AnalysisBaseClass.is_gendered(nltk.word_tokenize(cap.lower()), gender_type=gender):
                conf += 1
        return conf

    @staticmethod
    def convert_filenames_to_ids(fnames):
        """Converts a list of COCO filenames to list of corresponding ids."""
        new_list = []
        for fname in fnames:
            new_list.append(int(fname.split('.')[0].split('_')[2]))
        return new_list

    @staticmethod
    def is_gendered(words, gender_type='woman', man_word_list=['man'], woman_word_list=['woman']):
        """
        Returns true if the words in words contain
        a gender word from the specified gender type.
        If the caption contains more than one gender,
        return False.
        """
        m = False
        f = False
        check_m = (gender_type == 'man')
        check_f = (gender_type == 'woman')
        if len(set(words) & set(man_word_list)) > 0:
            m = True
        if len(set(words) & set(woman_word_list)) > 0:
            f = True
        if m & f:
            return False
        if m & check_m:
            return True
        elif f & check_f:
            return True
        else:
            return False

    @staticmethod
    def format_gt_captions(gt_file):
        gt = json.load(open(gt_file))
        gt_caps = []
        for annotation in gt['annotations']:
            gt_caps.append({'image_id': annotation['image_id'], 'caption': annotation['caption']})
        return gt_caps

    @staticmethod
    def simplify_anno_dict(img_2_anno_dict):
        img_2_anno_dict_simple = {}
        for key, value in img_2_anno_dict.items():
            id = int(key.split('_')[-1].split('.jpg')[0])
            img_2_anno_dict_simple[id] = {}
            img_2_anno_dict_simple[id]['male'] = value[0]
            img_2_anno_dict_simple[id]['female'] = int(not value[0])
            assert int(not value[0]) == value[1]

        return img_2_anno_dict_simple

    @staticmethod
    def get_shopping_split(fpath='/data1/caption_bias/models/research/im2txt/im2txt/data/raw-data/reducingbias/data/COCO/dev.data'):
        # TODO: move all data to one location and store dir as attribute
        """Returns desired split from men also like shopping as a list of filenames."""
        data = []
        samples = pickle.load(open(fpath, 'rb'))
        for sample in samples:
            data.append(sample['img'])

        return data

    # Static variables
    man_word_list_synonyms = ['boy', 'brother', 'dad', 'husband', 'man', 'groom', 'male', 'guy', 'men']
    woman_word_list_synonyms = ['girl', 'sister', 'mom', 'wife', 'woman', 'bride', 'female', 'lady', 'women']
    anno_dir = '/data1/caption_bias/models/research/im2txt/im2txt/data/raw-data/reducingbias/data/COCO/'
    target_train = os.path.join(anno_dir, 'train.data')
    target_val = os.path.join(anno_dir, 'dev.data')
    target_test = os.path.join(anno_dir, 'test.data')

    # create annotation dictionary and simplified anno dict
    img_2_anno_dict = create_dict_from_list(pickle.load(open(target_train, 'rb')))
    img_2_anno_dict.update(create_dict_from_list(pickle.load(open(target_test, 'rb'))))
    img_2_anno_dict.update(create_dict_from_list(pickle.load(open(target_val, 'rb'))))
    img_2_anno_dict_simple = simplify_anno_dict.__func__(img_2_anno_dict) # bleh
    # fetch ground truth captions and store in dict mapping id : caps
    gt_path = '/data1/coco/annotations_trainval2014/captions_only_valtrain2014.json'
    gt_caps_list = json.load(open(gt_path))['annotations']
    gt_caps = collections.defaultdict(list)
    for cap in gt_caps_list:
        gt_caps[int(cap['image_id'])].append(cap['caption'])


# TODO: make attribute of class
#caption paths
#all models
caption_paths = []
base_dir = ''
#base_dir = '/home/lisaanne/lev/'
#normal_training = ('normal training', base_dir + '/data1/caption_bias/models/research/im2txt/val_cap.json')
#caption_paths.append(normal_training)
#acl_nosum_ce = ('ACL (10) - no sum (CE)', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/train_blocked_ce.json')
#caption_paths.append(acl_nosum_ce)
# full_gender_set = ('full gender set', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/equalizer_all_gender_words.json')
# caption_paths.append(full_gender_set)
#baseline_ft_inception = ('baseline ft inception', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/ft_incep_captions_500k_bias_split.json')
#caption_paths.append(baseline_ft_inception)
#uw = ('uw 10x', base_dir + '/data2/caption-bias/result_jsons/LW10_ft-inception-fresh.json')
#caption_paths.append(uw)
#balanced = ('balanced', base_dir + '/data2/caption-bias/result_jsons/balance_man_woman_ft_inception.json')
#caption_paths.append(balanced)
#acl = ('acl', base_dir + '/data2/caption-bias/result_jsons/blocked_loss_w10_ft_incep_no_sum.json')
#caption_paths.append(acl)
#acl_conq = ('ACL Con-Q', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/quotient_loss_500k_iters.json')
#caption_paths.append(acl_conq)
#acl_conq_uw = ('ACL Con-Q UW', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/confusiont_quotient_UW.json')
#caption_paths.append(acl_conq_uw)
#acl_uw = ('ACL UW', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/train_blocked_U_10.json')
#caption_paths.append(acl_uw)
#acl_uw_ce = ('ACL UW CE', base_dir + '/data2/caption-bias/result_jsons/blocked_ce_LW10_ft-inception-fresh-iter1.500k.json')
#caption_paths.append(acl_uw_ce)
quotient = ('quotient', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/quotient_no_blocked_caps.json')
caption_paths.append(quotient)
#quotient_uw = ('quotient UW', base_dir +'/data2/kaylee/caption_bias/models/research/im2txt/captions/quotient_UW_10_500k_caps.json')
#caption_paths.append(quotient_uw)
#pytorch_model = ('pytorch_model', '/home/lisaanne/projects/sentence-generation/results/output.45950.ft-all-set.loss-acl10.ce-blocked.json')
#caption_paths.append(pytorch_model)
# uw_man5_woman15 = ('uw_man5_woman15', base_dir + '/data2/caption-bias/result_jsons/uw-man5-woman15_ft-inception-fresh.json')
# caption_paths.append(uw_man5_woman15)

#caption_paths = []
#base_dir = '/home/lisaanne/lev/'
baseline_ft_inception = ('baseline ft inception', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/ft_incep_captions_500k_bias_split.json')
caption_paths.append(baseline_ft_inception)
uw = ('uw 10x', base_dir + '/data2/caption-bias/result_jsons/LW10_ft-inception-fresh.json')
caption_paths.append(uw)
balanced = ('balanced', base_dir + '/data2/caption-bias/result_jsons/balance_man_woman_ft_inception.json')
caption_paths.append(balanced)
acl = ('acl', base_dir + '/data2/caption-bias/result_jsons/blocked_loss_w10_ft_incep_no_sum.json')
caption_paths.append(acl)
acl_conq = ('ACL Con-Q', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/quotient_loss_500k_iters.json')
caption_paths.append(acl_conq)

#quotient = ('quotient', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/captions/quotient_no_blocked_caps.json')
#caption_paths.append(quotient)

# rebuttal captions
equalizer = ('equalizer', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/rebuttal_captions/equalizer_retest.json')
caption_paths.append(equalizer)

all_gender_words = ('equalizer trained with larger set of gender words', base_dir + '/data2/kaylee/caption_bias/models/research/im2txt/rebuttal_captions/equalizer_all_gender_words.json')
caption_paths.append(all_gender_words)

pairs = ('equalizer loss with coco images without people', base_dir+'/data2/kaylee/caption_bias/models/research/im2txt/rebuttal_captions/selective_pairs.json')
caption_paths.append(pairs)
