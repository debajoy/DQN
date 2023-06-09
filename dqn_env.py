import gymnasium as gym
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import argparse
import numpy as np
from collections import deque, namedtuple
import sys
from torch.utils.tensorboard import SummaryWriter
writer = SummaryWriter("runs")
import matplotlib.pyplot as plt


class ExperienceReplay:
	""" 
	Based on the Replay Buffer implementation of TD3 
	Reference: https://github.com/sfujim/TD3/blob/master/utils.py
	"""
	def __init__(self, state_dim, action_dim,max_size,batch_size,gpu_index=0):
		self.max_size = max_size
		self.ptr = 0
		self.size = 0
		self.state = np.zeros((max_size, state_dim))
		self.action = np.zeros((max_size, action_dim))
		self.next_state = np.zeros((max_size, state_dim))
		self.reward = np.zeros((max_size, 1))
		self.done = np.zeros((max_size, 1))		
		self.batch_size = batch_size
		self.device = torch.device('cuda', index=gpu_index) if torch.cuda.is_available() else torch.device('cpu')


	def add(self, state, action,reward,next_state, done):
		self.state[self.ptr] = state
		self.action[self.ptr] = action
		self.next_state[self.ptr] = next_state
		self.reward[self.ptr] = reward
		self.done[self.ptr] = done
		self.ptr = (self.ptr + 1) % self.max_size
		self.size = min(self.size + 1, self.max_size)

	def sample(self):
		ind = np.random.randint(0, self.size, size=self.batch_size)

		return (
			torch.FloatTensor(self.state[ind]).to(self.device),
			torch.FloatTensor(self.action[ind]).long().to(self.device),
			torch.FloatTensor(self.reward[ind]).to(self.device),
			torch.FloatTensor(self.next_state[ind]).to(self.device),
			torch.FloatTensor(self.done[ind]).to(self.device)
		)



class QNetwork(nn.Module):
	"""
	Q Network: designed to take state as input and give out Q values of actions as output
	"""

	def __init__(self, state_dim, action_dim):
		"""
			state_dim (int): state dimenssion
			action_dim (int): action dimenssion
		"""
		super(QNetwork, self).__init__()
		self.l1 = nn.Linear(state_dim, 64)
		self.l2 = nn.Linear(64, 64)
		self.l3 = nn.Linear(64, action_dim)
		
	def forward(self, state):
		q = F.relu(self.l1(state))
		q = F.relu(self.l2(q))
		return self.l3(q)



class DQNAgent():

	def __init__(self,
	 state_dim, 
	 action_dim,
	 discount=0.99,
	 tau=1e-3,
	 lr=5e-4,
	 update_freq=4,
	 max_size=int(1e5),
	 batch_size=64,
	 gpu_index=0
	 ):
		"""
			state_size (int): dimension of each state
			action_size (int): dimension of each action
			discount (float): discount factor
			tau (float): used to update q-target
			lr (float): learning rate
			update_freq (int): update frequency of target network
			max_size (int): experience replay buffer size
			batch_size (int): training batch size
			gpu_index (int): GPU used for training
		"""
		self.state_dim = state_dim
		self.action_dim = action_dim
		self.discount = discount
		self.tau = tau
		self.lr = lr
		self.update_freq = update_freq
		self.batch_size = batch_size
		self.device = torch.device('cuda', index=gpu_index) if torch.cuda.is_available() else torch.device('cpu')


		# Setting up the NNs
		self.Q = QNetwork(state_dim, action_dim).to(self.device)
		self.Q_target = QNetwork(state_dim, action_dim).to(self.device)
		self.optimizer = optim.Adam(self.Q.parameters(), lr=self.lr)

		# Experience Replay Buffer
		self.memory = ExperienceReplay(state_dim,1,max_size,self.batch_size,gpu_index)
		
		self.t_train = 0
	
	def step(self, state, action, reward, next_state, done):
		"""
		1. Adds (s,a,r,s') to the experience replay buffer, and updates the networks
		2. Learns when the experience replay buffer has enough samples
		3. Updates target netowork
		"""
		self.memory.add(state, action, reward, next_state, done)	   
		self.t_train += 1 
					
		if self.memory.size > self.batch_size:
			experiences = self.memory.sample()
			self.learn(experiences, self.discount) #To be implemented
		
		if (self.t_train % self.update_freq) == 0:
			self.target_update(self.Q, self.Q_target, self.tau) #To be implemented 

	def select_action(self, state, epsilon=0.):
		"""
		TODO: Complete this block to select action using epsilon greedy exploration 
		strategy
		Input: state, epsilon
		Return: Action
		Return Type: int	
		"""
		###### TYPE YOUR CODE HERE ######
		if np.random.random()<epsilon:
			return np.random.choice(self.action_dim)
		else:
			state = torch.tensor(state).to(self.device)
			action = torch.argmax(self.Q(state)).item()
			return action
		################################# 

	def learn(self, experiences, discount):
		"""
		TODO: Complete this block to update the Q-Network using the target network
		1. Compute target using  self.Q_target ( target = r + discount * max_b [Q_target(s,b)] )
		2. Compute Q(s,a) using self.Q
		3. Compute MSE loss between step 1 and step 2
		4. Update your network
		Input: experiences consisting of states,actions,rewards,next_states and discount factor
		Return: None
		""" 		
		states, actions, rewards, next_states, dones = experiences
		#cleprint(actions)
		###### TYPE YOUR CODE HERE ######
		#state = states.to(self.device)
		#actions = actions.to(self.device)
		#rewards = rewards.to(self.device)
		#next_state = next_states.to(self.device)
		#self.Q.train()
		y = self.Q(states).gather(1,actions)
		#print(y.shape)
		#print("shape of the y:",rewards.shape)
		#self.Q_target.eval()
		action = self.Q_target(next_states).detach()
		max_action = action.max(1)[0].unsqueeze(1)
		y_hat = rewards+discount*max_action*(1-dones)
		#print(y,y_hat)
		#print("shape of y_hat",y_hat.shape)
		criterion = nn.MSELoss()
		loss = criterion(y,y_hat)
		self.optimizer.zero_grad()
		loss.backward()
		self.optimizer.step()
		self.target_update(self.Q,self.Q_target,self.tau)
		#################################


		                    

	def target_update(self, Q, Q_target, tau):
		"""
		TODO: Update the target network parameters (param_target) using current Q parameters (param_Q)
		Perform the update using tau, this ensures that we do not change the target network drastically
		1. param_target = tau * param_Q + (1 - tau) * param_target
		Input: Q,Q_target,tau
		Return: None
		""" 
		###### TYPE YOUR CODE HERE ######
		#with torch.no_grad():
		
		for target_param, local_param in zip(self.Q_target.parameters(),self.Q.parameters()):
			target_param.data.copy_(tau*local_param.data + (1-tau)*target_param.data)
		#################################


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--env", default="CartPole-v1")          # Gymnasium environment name
	parser.add_argument("--seed", default=0, type=int)              # sets Gym, PyTorch and Numpy seeds
	parser.add_argument("--n-episodes", default=1500, type=int)     # maximum number of training episodes
	parser.add_argument("--batch-size", default=64, type=int)       # training batch size
	parser.add_argument("--discount", default=0.99)                 # discount factor
	parser.add_argument("--lr", default=1e-4)                       # learning rate
	parser.add_argument("--tau", default=0.005)                     # soft update of target network
	parser.add_argument("--max-size", default=int(1e5),type=int)    # experience replay buffer length
	parser.add_argument("--update-freq", default=4, type=int)       # update frequency of target network
	parser.add_argument("--gpu-index", default=0,type=int)		    # GPU index
	parser.add_argument("--max-esp-len", default=1000, type=int)    # maximum time of an episode
	#exploration strategy
	parser.add_argument("--epsilon-start", default=0.09)               # start value of epsilon
	parser.add_argument("--epsilon-end", default=0.05)              # end value of epsilon
	parser.add_argument("--epsilon-decay", default=0.995)           # decay value of epsilon
	args = parser.parse_args()

	# making the environment	
	env = gym.make(args.env)

	#setting seeds
	torch.manual_seed(args.seed)
	np.random.seed(args.seed)
	random.seed(args.seed)

	state_dim = env.observation_space.shape[0]
	action_dim = env.action_space.n

	kwargs = {
		"state_dim":state_dim,
		"action_dim":action_dim,
		"discount":args.discount,
	 	"tau":args.tau,
	 	"lr":args.lr,
	 	"update_freq":args.update_freq,
	 	"max_size":args.max_size,
	 	"batch_size":args.batch_size,
	 	"gpu_index":args.gpu_index
	}	
	learner = DQNAgent(**kwargs) #Creating the DQN learning agent
	score =[]
	moving_window = deque(maxlen=100)
	epsilon = args.epsilon_start
	for e in range(args.n_episodes):
		state, _ = env.reset(seed=args.seed)
		curr_reward = 0
		for t in range(args.max_esp_len):
			action = learner.select_action(state,epsilon) #To be implemented
			n_state,reward,terminated,truncated,_ = env.step(action)
			done = terminated or truncated 
			learner.step(state,action,reward,n_state,done) #To be implemented
			state = n_state
			curr_reward += reward
			if done:
				break
		moving_window.append(curr_reward)
		score.append(curr_reward)

		""""
		TODO: Write code for decaying the exploration rate using args.epsilon_decay
		and args.epsilon_end. Note that epsilon has been initialized to args.epsilon_start  
		1. You are encouraged to try new methods
		"""
		###### TYPE YOUR CODE HERE ######
		epsilon = max(epsilon*args.epsilon_decay,args.epsilon_end)
		#################################	
		
		if e % 100 == 0:
			print('Episode Number {} Average Episodic Reward (over 100 episodes): {:.2f}'.format(e, np.mean(moving_window)))
			writer.add_scalar('Episodic Rewards vs training iterations for cartpole with eps_end=0.05',np.mean(moving_window),e)
		""""
		TODO: Write code for
		1. Logging and plotting
		2. Rendering the trained agent 
		"""
	###### TYPE YOUR CODE HERE ######
		writer.close()
		#Now that we have trained the environment lets render it
	
	#################################
