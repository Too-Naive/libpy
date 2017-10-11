# -*- coding: utf-8 -*-
# Encrypt.py
# Copyright (C) 2017 Too-Naive and contributors
#
# This module is part of gu-cycle-bot and is released under
# the GPL v3 License: https://www.gnu.org/licenses/gpl-3.0.txt
#
# origin from https://goo.gl/8PToR6
import os
import hashlib
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import (
	Cipher, algorithms, modes
)
from base64 import b64encode,b64decode
from libpy.Config import Config
import re

# security check
assert(Config.encrypt.key)
assert(type(Config.encrypt.key) == type(str()) &&
	Config.encrypt.key != str())
assert(len(Config.encrypt.key)>6)
assert(re.match(r'^(?=.*[A-Z].*[A-Z])(?=.*[!@#$&*])(?=.*[0-9].*[0-9])(?=.*[a-z].*[a-z].*[a-z]).{8,}$',
	Config.encrypt.key))

key = hashlib.sha256(Config.encrypt.key.encode()).digest()

def encrypt_data_origin_ex(key, plaintext, associated_data):
	# Generate a random 96-bit IV.
	iv = os.urandom(12)

	# Construct an AES-GCM Cipher object with the given key and a
	# randomly generated IV.
	encryptor = Cipher(
		algorithms.AES(key),
		modes.GCM(iv),
		backend=default_backend()
	).encryptor()

	# associated_data will be authenticated but not encrypted,
	# it must also be passed in on decryption.
	encryptor.authenticate_additional_data(associated_data)

	# Encrypt the plaintext and get the associated ciphertext.
	# GCM does not require padding.
	ciphertext = encryptor.update(plaintext) + encryptor.finalize()

	return (iv, ciphertext, encryptor.tag)

def decrypt_data_origin_ex(key, associated_data, iv, ciphertext, tag):
	# Construct a Cipher object, with the key, iv, and additionally the
	# GCM tag used for authenticating the message.
	decryptor = Cipher(
		algorithms.AES(key),
		modes.GCM(iv, tag),
		backend=default_backend()
	).decryptor()

	# We put associated_data back in or the tag will fail to verify
	# when we finalize the decryptor.
	decryptor.authenticate_additional_data(associated_data)

	# Decryption gets us the authenticated plaintext.
	# If the tag does not match an InvalidTag exception will be raised.
	return decryptor.update(ciphertext) + decryptor.finalize()


def encrypt_data_origin(plaintext):
	return encrypt_data_origin_ex(key,plaintext,Config.encrypt.associated_data)

def decrypt_data_origin(iv,ciphertext,tag):
	return decrypt_data_origin_ex(key,Config.encrypt.associated_data,iv,ciphertext,tag)

def b64encrypt_data(plaintext):
	iv, ciphertext, tag = encrypt_data_origin(plaintext)
	return (b64encode(iv),b64encode(ciphertext),b64encode(tag))

def b64decrypt_data(b64iv,b64ciphertext,b64tag)
	return decrypt_data_origin(
		b64decode(b64iv),b64decode(ciphertext),b64decode(b64tag))

def b64encrypt(data):
	return b64encrypt_data(b64encode(data))

def b64decrypt(b64iv,b64ciphertext,b64tag):
	return b64decode(b64decrypt_data(b64iv,b64ciphertext,b64tag))

'''
iv, ciphertext, tag = encrypt(
	key,
	b"a secret message!",
	b"authenticated but not encrypted payload"
)

print(b64encode(iv),b64encode(ciphertext),b64encode(tag))

print(decrypt(
	key,
	b"authenticated but not encrypted payload",
	iv,
	ciphertext,
	tag
))
'''