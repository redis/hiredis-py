### 0.1.6 (unreleased)

### 0.1.5

* Fix memory leak when many reader instances are created (see #26).

### 0.1.4

* Allow any buffer compatible object as argument to feed (see #22).

### 0.1.3

* Allow `protocolError` and `replyError` to be any type of callable (see #21).

### 0.1.2

* Upgrade hiredis to 0.11.0 to support deeply nested multi bulk replies.
