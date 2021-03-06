#!/usr/bin/env python3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from mesa.batchrunner import BatchRunner
import logging
import time
import subprocess
import sys
import glob

logging.basicConfig(level=logging.WARNING)


class CitizenAgent(Agent):

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        logging.info("Instantiating citizen {}.".format(self.unique_id))
        self.opinions = model.random.uniform(0,1,size=model.num_issues)

    def step(self):
        logging.info("Running citizen {}...".format(self.unique_id))
        neis = self.model.G.adj[self.unique_id]
        if len(neis) == 0:
            logging.info("  Agent {} has no neighbors!".format(self.unique_id))
        else:
            nei = self.model.schedule.agents[self.model.random.choice(neis)]
            compare, persuade = self.model.random.choice(
                np.arange(0,len(self.opinions)), size=2, replace=False)
            if (np.abs(self.opinions[compare] - nei.opinions[compare]) 
                    > self.model.Cthresh):
                logging.info("  Agent {} thinks {} is a kook.".format(
                    self.unique_id, nei.unique_id))
            else:
                logging.info("  Agent {} listens to {}...".format(
                    self.unique_id, nei.unique_id))
                self.opinions[persuade] = \
                    (self.opinions[persuade] + nei.opinions[persuade]) / 2
        

    def __str__(self):
        return "Agent {}".format(self.unique_id)

    def __repr__(self):
        return "Agent {}".format(self.unique_id)


def get_opinion(model, agent_num, issue_num):
    print("get_opinion({}) for agent {}".format(issue_num, agent_num))
    return model.schedule.agents[agent_num].opinions[issue_num]


def mean_opinion_var(model):
    return np.array(
        [ np.array([ c.opinions[i] for c in model.schedule.agents ])
            for i in range(model.num_issues)
        ]).var()


class SocialWorld(Model):

    """
    T - max number of iterations
    N - number of citizens
    I - number of issues citizens have an opinion on
    Cthresh - comparison threshold for compare/persuade mechanic
    ER_p - probability of edge for ER model
    """
    def __init__(self, T, N, I, Cthresh, ER_p):

        logging.info("Initializing SocialWorld({},{},{},{},{})...".format(
            T,N,I,Cthresh,ER_p))

        # https://github.com/projectmesa/mesa/issues/958#issuecomment-733651008
        self.random = np.random.default_rng(123)
        
        self.max_steps = T
        self.num_agents = N
        self.num_issues = I
        self.Cthresh = Cthresh
        self.p = ER_p
        self.schedule = RandomActivation(self)
        self.num_steps = 0
        self.G = nx.erdos_renyi_graph(N, ER_p)
        while not nx.is_connected(self.G):
            self.G = nx.erdos_renyi_graph(N, ER_p)

        # Attaching each CitizenAgent object to one of the graph's node's
        # attribute dicts. (Seems nicer to make the node actually *be* the
        # CitizenAgent, but can't figure out how to do this in networkx when
        # generating a random graph.)
        for i in range(self.num_agents):
            c = CitizenAgent(i, self)
            self.G.nodes[i]["citizen"] = c
            self.schedule.add(c)
        self.running = True   # could set this to stop prematurely

        self.datacollector = DataCollector(
            agent_reporters={},
            model_reporters={
                "agent"+str(a)+"_iss"+str(i):
                    lambda model, n=a, m=i: get_opinion(model,n,m)
                        for a in range(4) for i in range(3) 
            })

    def step(self):
        if not self.running:
            return
        if self.num_steps >= self.max_steps:
            logging.info("Simulation completed in {} iterations."
                .format(self.num_steps))
            self.running = False
        self.num_steps += 1
        logging.debug("Iteration {}...".format(self.num_steps))
        self.datacollector.collect(self)
        self.schedule.step()


    def run(self):
        for _ in range(self.max_steps):
            self.step()


def make_plots(model):

    df = model.datacollector.get_model_vars_dataframe()

    plt.clf()
    plt.plot(df['MeanOpinionVar'],
        color='green',linewidth=2)
    plt.ylim((0,df['MeanOpinionVar'].max()*1.1))
    plt.xlabel('Iteration')
    plt.ylabel(r'$\mu_{opinion(\sigma^2)}$',fontsize=16)
    plt.title("Mean opinion variance over time")
    plt.savefig('meanOpinionVar.png')


if __name__ == "__main__":

    if len(sys.argv) <= 1:
        print("Usage: polar.py single|batch.")
        sys.exit()

    if sys.argv[1] == "single":

        # Single simulation run.
        m = SocialWorld(400, 40, 10, 0.05, .2)
        m.run()
        make_plots(m)

    else:

        # Batch simulation run.
        pass
#        fixed = {"p":.2}
#        variable_params = {"N": np.arange(10,100,5)}
#
#        batch_run = BatchRunner(SocialWorld, variable_params, fixed,
#            iterations=10, max_steps=1000,
#            model_reporters={"lambda":compute_lambda,
#                "itersToConverge": iters_to_converge})
#
#        batch_run.run_all()
#        df = batch_run.get_model_vars_dataframe()
#        plt.figure()
#        plt.scatter(df["lambda"], df.itersToConverge)
#        plt.show()
#
#        dfagg = df.groupby("lambda").itersToConverge.mean()
#        plt.figure()
#        plt.plot(dfagg.index,dfagg)
#        plt.show()
