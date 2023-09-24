

from ga.algorithm import Algorithm
from sqlalchemy.orm import Session
from fastapi import Depends
import numpy as np
import math 

from db.database import get_db
from db.repositories import UserRepository, MovieRepository, RatingsRepository

class MyGeneticAlgorithm(Algorithm):

    def __init__(self, query_search, individual_size, population_size, p_crossover, p_mutation, all_ids, max_generations=100, size_hall_of_fame=1, fitness_weights=(1.0, ), seed=42, db=None) -> None:
        super().__init__(
            individual_size, 
            population_size, 
            p_crossover, 
            p_mutation, 
            all_ids, 
            max_generations, 
            size_hall_of_fame, 
            fitness_weights, 
            seed)

        self.db = db
        self.all_ids = all_ids
        self.query_search = query_search
        

    
    def evaluate(self, individual):

        #self.query_search codigo da pessoa
        #individual lista de codigo dos filmes

        if len(individual) != len(set(individual)):
            return (0.0, )
        
        if len(list(set(individual) - set(self.all_ids))) > 0:
            return (0.0, )
        
        ratings_movies_user = RatingsRepository.find_by_userid(self.db, self.query_search)
        ratings_movies = RatingsRepository.find_by_movieid_list(self.db, individual)

        if len(ratings_movies_user) == 0:
            return (0.0, )
        
        if len(ratings_movies) == 0:
            return (0.0, )
        
        
        #pega os generos mais assistidos pelo usuario
        genres_user = []
        for movie in ratings_movies_user:
            genres_user.append(MovieRepository.find_by_id(self.db, movie.movieId).genres)

        genres_user = [item for sublist in genres_user for item in sublist.split('|')]

        #pega os 3 generos mais assistidos pelo usuario
        genres_user = list(dict.fromkeys(genres_user))
        genres_user = genres_user[:3]
        

        #pega os filmes que tenham os generos mais assistidos pelo usuario
        genres_user_set = set(genres_user)
        movies_user = []

        for movie in ratings_movies:
            genres_movie = set(MovieRepository.find_by_id(self.db, movie.movieId).genres.split('|'))
            if genres_movie & genres_user_set:  # Verifica interseção de conjuntos (se têm gêneros em comum)
                movies_user.append(movie.movieId)

        
        #dos filmes que tem os generos mais assistidos pelo usuario, pega os que o usuario ainda nao assistiu
        movies_user = list(set(movies_user) - set([movie.movieId for movie in ratings_movies_user]))

        #pega os filmes com as maiores notas dos generos mais assistidos pelo usuario
        movies_user_not_watched = []
        movies_user_not_watched = RatingsRepository.find_by_movieid_list(self.db, movies_user)
        movies_user_not_watched.sort(key=lambda x: x.rating, reverse=True)

        #pega a nota media para cada filmes que o usuario ainda nao assistiu
        movies_user_not_watched_mean = [
                {
                    'movieId': movie.movieId,
                    'mean': np.mean([obj_.rating for obj_ in RatingsRepository.find_by_movieid(self.db, movie.movieId)])
                }
                for movie in movies_user_not_watched
            ]

        #pega a nota media dos filmes que o usuario ja assistiu
        mean_user = 0.0
        if len(ratings_movies_user) > 0:
            mean_user = np.mean([obj_.rating for obj_ in ratings_movies_user])
        else:
            mean_user = 0.0
        

        #pega todos os filmes que tenham a media maior que a media do usuario
        movies_user_not_watched_mean = [movie for movie in movies_user_not_watched_mean if movie['mean'] > mean_user]

        #mega a media dos filmes que tenham a media maior que a media do usuario
        mean_movies_user_not_watched_mean = 0.0
        if len(movies_user_not_watched_mean) > 0:
            mean_movies_user_not_watched_mean = np.mean([obj_['mean'] for obj_ in movies_user_not_watched_mean])
        else:
            mean_movies_user_not_watched_mean = 0.0


        #pega o ano de lancamento dos filmes que o usuario ja assistiu
        years_user = [MovieRepository.find_by_id(self.db, movie.movieId).year for movie in ratings_movies_user]


        #pega a media dos anos de lancamento dos filmes que o usuario ja assistiu
        mean_years_user = 0.0
        if len(years_user) > 0:
            mean_years_user = np.mean(years_user)
        else:
            mean_years_user = 0.0

        #pega todos os filmes que tenham o ano de lançamento proximo da media dos anos de lancamento dos filmes que o usuario ja assistiu (5 anos de diferença para maimovies_user_not_watched_mean s ou para menos))) 
        movies_years_user_not_watched_mean = []
        for movie in movies_user_not_watched:
            if  mean_user + 5 > abs(MovieRepository.find_by_id(self.db, movie.movieId).year) > mean_years_user - 5:
                movies_years_user_not_watched_mean.append(movie.movieId)

        fitness = 0.0
        fitness += mean_movies_user_not_watched_mean * 0.3 #nota media dos filmes que o usuario nao assistiu e tem media maior que a media do usuario
        fitness += len(movies_user_not_watched_mean) * 0.1#numero de filmes que o usuario nao assistiu e tem media maior que a media do usuario
        fitness += mean_user * 0.2 #nota media dos filmes que o usuario ja assistiu
        fitness += mean_years_user * 0.1#media dos anos de lancamento dos filmes que o usuario ja assistiu
        fitness += len(movies_years_user_not_watched_mean) * 0.3 #numero de filmes que o usuario nao assistiu e tem media maior que a media do usuario e tem o ano de lancamento proximo da media dos anos de lancamento dos filmes que o usuario ja assistiu (5 anos de diferença para mais ou para menos)))


        print(fitness)

        #media final igual a nota media dos filmes q o usuario nao assistiu e tem media maior que a media do usuario + numero de filmes que o usuario nao assistiu e tem media maior que a media do usuario + nota media dos filmes que o usuario ja assistiu
        return (fitness,  )
        

