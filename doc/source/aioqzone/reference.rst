References
========================

--------------------
Terms
--------------------

Here we will explain some common used abbreviation and alias in aioqzone.

.. glossary::

    abstime
        A timestamp represents when the feed is created.
        All feeds have this field. If not, generate a persudo one is easy.

        In Qzone interface, this is called ``created_time`` sometimes.

    appid
        Specifies where the feed is created. For example, the app id of "emotion" is 311,
        202 means shares from Wechat or other apps.

    fid
        Means "feed id". All "emotion" feed has a **unique** fid, but other app such as shares do not.
        For those apps, their `fid` field might be a fixed string.

        In Qzone interface, `fid` is also named as ``tid``, ``feedkey``, etc.

    uin
        Known as ``QQ``, which identifies an account.
