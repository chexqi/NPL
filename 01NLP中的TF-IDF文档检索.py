import numpy as np
from collections import Counter
import itertools
from visual import show_tfidf

docs = [
	"it is a good day, I like to stay here",
	"I am happy to be here",
	"I am bob",
	"it is sunny today",
	"I have a party today",
	"it is a dog and that is a cat",
	"there are dog and cat on the tree",
	"I study hard this morning",
	"today is a good day",
	"tomorrow will be a good day",
	"I like coffee, I like book and I like apple",
	"I do not like it",
	"I am kitty, I like bob",
	"I do not care who like bob, but I like kitty",
	"It is coffee time, bring your cup",
]

# %% 将文档的单词转换成ID形式，这样便于后续通过ID进行统计。
docs_words = [d.replace(",", "").split(" ") for d in docs]      # 将所有文档转换为一个一个词组成的列表
# for doc_word in docs_words:
# 	print(doc_word)
vocab = set(itertools.chain(*docs_words))   # 所有词组成的集合，没有重复的元素
# print(vocab)
v2i = {v: i for i, v in enumerate(vocab)}
i2v = {i: v for v, i in v2i.items()}
# print(v2i)
# print(i2v)

# %% 提供四种tf计算方法，3中idf计算方法
def safe_log(x):
	mask = x != 0
	x[mask] = np.log(x[mask])
	return x
tf_methods = {
	"log": lambda x: np.log(1+x),
	"augmented": lambda x: 0.5 + 0.5 * x / np.max(x, axis=1, keepdims=True),
	"boolean": lambda x: np.minimum(x, 1),
	"log_avg": lambda x: (1 + safe_log(x)) / (1 + safe_log(np.mean(x, axis=1, keepdims=True))),
}
idf_methods = {
	"log": lambda x: 1 + np.log(len(docs) / (x+1)),
	"prob": lambda x: np.maximum(0, np.log((len(docs) - x) / (x+1))),
	"len_norm": lambda x: x / (np.sum(np.square(x))+1),
}


def get_tf(method="log"):
	'''
	词频term frequency: how frequent a word appears in a doc
	每个文档都需要计算一个词频向量
	:param method:
	:return:
	'''
	_tf = np.zeros((len(vocab), len(docs)), dtype=float)    # [n_vocab, n_doc]
	for i, d in enumerate(docs_words):
		counter = Counter(d)
		for v in counter.keys():
			_tf[v2i[v], i] = counter[v] / counter.most_common(1)[0][1]

	weighted_tf = tf_methods.get(method, None)
	if weighted_tf is None:
		raise ValueError
	return weighted_tf(_tf)


def get_idf(method="log"):
	'''
	逆文本频率指数inverse document frequency: low idf for a word appears in more docs, mean less important
	idf在语料库中计算后的结果，也需要用来作为搜索问题的idf
	:param method:
	:return:
	'''
	df = np.zeros((len(i2v), 1))
	for i in range(len(i2v)):
		d_count = 0
		for d in docs_words:
			d_count += 1 if i2v[i] in d else 0
		df[i, 0] = d_count

	idf_fn = idf_methods.get(method, None)
	if idf_fn is None:
		raise ValueError
	return idf_fn(df)


def cosine_similarity(q, _tf_idf):
	'''
	余弦相似度
	:param q:
	:param _tf_idf:
	:return:
	'''
	unit_q = q / np.sqrt(np.sum(np.square(q), axis=0, keepdims=True))
	unit_ds = _tf_idf / np.sqrt(np.sum(np.square(_tf_idf), axis=0, keepdims=True))
	similarity = unit_ds.T.dot(unit_q).ravel()
	return similarity


def docs_score(q, len_norm=False):
	'''
	测试搜索时，只需要将搜索的问题向量化，把搜索向量在文档向量上进行距离计算，就能算出来哪些文档更贴近搜索向量了。
	:param q:
	:param len_norm:
	:return:
	'''
	q_words = q.replace(",", "").split(" ")
	# add unknown words
	unknown_v = 0
	for v in set(q_words):
		if v not in v2i:
			v2i[v] = len(v2i)
			i2v[len(v2i)-1] = v
			unknown_v += 1
	if unknown_v > 0:
		_idf = np.concatenate((idf, np.zeros((unknown_v, 1), dtype=float)), axis=0)
		_tf_idf = np.concatenate((tf_idf, np.zeros((unknown_v, tf_idf.shape[1]), dtype=float)), axis=0)
	else:
		_idf, _tf_idf = idf, tf_idf
	counter = Counter(q_words)
	q_tf = np.zeros((len(_idf), 1), dtype=float)     # [n_vocab, 1]
	for v in counter.keys():
		q_tf[v2i[v], 0] = counter[v]

	q_vec = q_tf * _idf            # [n_vocab, 1]，搜索问题的tf-idf向量表达

	q_scores = cosine_similarity(q_vec, _tf_idf)        # 计算余弦相似度
	if len_norm:
		len_docs = [len(d) for d in docs_words]
		q_scores = q_scores / np.array(len_docs)
	return q_scores


def get_keywords(n=2):
	'''
	为文档找出关键词
	:param n:
	:return:
	'''
	for c in range(3):
		col = tf_idf[:, c]
		idx = np.argsort(col)[-n:]
		print("doc{}, top{} keywords {}".format(c, n, [i2v[i] for i in idx]))

# %% 建立检索库
tf = get_tf()           # [n_vocab, n_doc]
idf = get_idf()         # [n_vocab, 1]
tf_idf = tf * idf       # [n_vocab, n_doc]
print("tf shape(vecb in each docs): ", tf.shape)
print("\ntf samples:\n", tf[:2])
print("\nidf shape(vecb in all docs): ", idf.shape)
print("\nidf samples:\n", idf[:2])
print("\ntf_idf shape: ", tf_idf.shape)
print("\ntf_idf sample:\n", tf_idf[:2])


# %% 测试
get_keywords()
q = "I get a coffee cup"
scores = docs_score(q)
d_ids = scores.argsort()[-3:][::-1]
print("\ntop 3 docs for '{}':\n{}".format(q, [docs[i] for i in d_ids]))

# %% 显示每篇文档的tf-idf向量
show_tfidf(tf_idf.T, [i2v[i] for i in range(tf_idf.shape[0])], "tfidf_matrix")
