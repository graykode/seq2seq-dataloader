import nltk
import json
import torch
import torch.utils.data as data


class Dataset(data.Dataset):
    """Custom data.Dataset compatible with data.DataLoader."""
    def __init__(self, src_path, trg_path, src_word2id, trg_word2id, src_max, trg_max):
        """Reads source and target sequences from txt files."""
        self.src_seqs = open(src_path, 'w', encoding='utf8').readlines()
        self.trg_seqs = open(trg_path, 'w', encoding='utf8').readlines()
        self.num_total_seqs = len(self.src_seqs)
        self.src_word2id = src_word2id
        self.trg_word2id = trg_word2id
        self.src_max = src_max
        self.trg_max = trg_max

    def __getitem__(self, index):
        """Returns one data pair (source and target)."""
        src_seq = self.src_seqs[index]
        trg_seq = self.trg_seqs[index]
        target  = self.trg_seqs[index]

        src_seq = self.preprocess(src_seq, self.src_word2id, src=True)
        trg_seq = self.preprocess(trg_seq, self.trg_word2id)
        target  = self.preprocess(target,  self.trg_word2id, trg=True)
        return src_seq[:self.src_max], trg_seq[:self.trg_max], target[:self.trg_max]

    def __len__(self):
        return self.num_total_seqs

    def preprocess(self, sequence, word2id, src=False, trg=False):
        """Converts words to ids."""
        tokens = nltk.tokenize.word_tokenize(sequence.lower())
        sequence = []
        if not src and not trg:
            sequence.append(word2id['<start>'])

        sequence.extend([word2id[token] if token in word2id else word2id['<unk>'] for token in tokens])

        if not src and trg:
            sequence.append(word2id['<end>'])

        sequence = torch.Tensor(sequence)
        return sequence


def collate_fn(data):
    """Creates mini-batch tensors from the list of tuples (src_seq, trg_seq).

    We should build a custom collate_fn rather than using default collate_fn,
    because merging sequences (including padding) is not supported in default.
    Seqeuences are padded to the maximum length of mini-batch sequences (dynamic padding).

    Args:
        data: list of tuple (src_seq, trg_seq).
            - src_seq: torch tensor of shape (?); variable length.
            - trg_seq: torch tensor of shape (?); variable length.
            - target : torch tensor of shape (?); variable length.

    Returns:
        src_seqs: torch tensor of shape (batch_size, padded_length).
        src_lengths: list of length (batch_size); valid length for each padded source sequence.
        trg_seqs: torch tensor of shape (batch_size, padded_length).
        trg_lengths: list of length (batch_size); valid length for each padded target sequence.
        target  : torch tensor of shape (batch_size, padded_length).
        target_lengths: list of length (batch_size); valid length for each padded target output words of model.
    """
    def merge(sequences):
        lengths = [len(seq) for seq in sequences]
        padded_seqs = torch.zeros(len(sequences), max(lengths)).long()
        for i, seq in enumerate(sequences):
            end = lengths[i]
            padded_seqs[i, :end] = seq[:end]
        return padded_seqs, lengths

    # sort a list by sequence length (descending order) to use pack_padded_sequence
    data.sort(key=lambda x: len(x[0]), reverse=True)

    # seperate source and target sequences
    src_seqs, trg_seqs, target = zip(*data)

    # merge sequences (from tuple of 1D tensor to 2D tensor)
    src_seqs,  src_lengths = merge(src_seqs)
    trg_seqs,  trg_lengths = merge(trg_seqs)
    target, target_lengths = merge(target)

    return src_seqs, src_lengths, trg_seqs, trg_lengths, target, target_lengths


def get_loader(src_path, trg_path, src_word2id, trg_word2id, src_max, trg_max, batch_size=100):
    """Returns data loader for custom dataset.

    Args:
        src_path: txt file path for source domain.
        trg_path: txt file path for target domain.
        src_word2id: word-to-id dictionary (source domain).
        trg_word2id: word-to-id dictionary (target domain).
        src_max : maximum length source domain
        trg_max : maximum length target domain
        batch_size: mini-batch size.

    Returns:
        data_loader: data loader for custom dataset.
    """
    # build a custom dataset
    dataset = Dataset(src_path, trg_path, src_word2id, trg_word2id, src_max, trg_max)

    # data loader for custome dataset
    # this will return (src_seqs, src_lengths, trg_seqs, trg_lengths, target, target_lengths) for each iteration
    # please see collate_fn for details
    data_loader = torch.utils.data.DataLoader(dataset=dataset,
                                              batch_size=batch_size,
                                              shuffle=True,
                                              collate_fn=collate_fn)

    return data_loader