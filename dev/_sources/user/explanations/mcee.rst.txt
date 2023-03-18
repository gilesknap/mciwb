.. _mcee:

Comparison with Minecraft Education Edition
===========================================

Introduction
------------

Minecraft Education Edition (MC EE) is a version of Minecraft that is designed
for use in schools. It provides an in game editor for making python or scratch
code to create in and interact with Minecraft worlds.

When I started working on MCIWB, I took a brief look at MC EE. But dismissed it
as out of date and not well supported. That was a mistake. The Hacker News
discussion `here <https://news.ycombinator.com/item?id=35166874#35195105>`_
encouraged me to take another look.

This page details my findings on investigating MC EE in more depth and
discusses the differences between MC EE and MCIWB.

TODO - Work in Progress

MCWIB perf Results
------------------

Results for tower function in MCIWB::


    In [4]: from demo.shapes import tower

    In [5]: start= Vec3(632, 73, -1724)

    In [6]: tower(start, 9, 5, Item.AIR)
    WARNING:root:tower took 0.141305 seconds
