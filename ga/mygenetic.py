

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
        
        self.lista_filmes_usuario_asistiu =  RatingsRepository.find_by_userid(self.db, self.query_search)
        print(self.lista_filmes_usuario_asistiu)
        ratings_usuario = RatingsRepository.find_by_userid(self.db, self.query_search)
        self.media_nota_filmes_usuario_asistiu = sum([
            x.rating for x in ratings_usuario
        ]) / len(ratings_usuario)

        self.media_ano_filmes_usuario_asistiu = np.mean([MovieRepository.find_by_id(self.db, x.movieId).year for x in self.lista_filmes_usuario_asistiu])


        # Pega os gêneros dos filmes assistidos pelo usuário
        generos = [MovieRepository.find_by_id(self.db, x.movieId).genres for x in self.lista_filmes_usuario_asistiu]
        # Divide os gêneros e cria uma lista única
        generos_split = [g for sublist in generos for g in sublist.split('|')]
        # Conta as ocorrências de cada gênero
        contagem_generos = {}
        for gen in generos_split:
            contagem_generos[gen] = contagem_generos.get(gen, 0) + 1
        # Pega os três gêneros mais comuns
        sorted_generos = sorted(contagem_generos.keys(), key=lambda x: contagem_generos[x], reverse=True)
        self.lista_generos_usuario = sorted_generos[:3]


        

    def evaluate(self, individual):
        
        """
        Avalia a adequação (fitness) de um indivíduo com base em critérios de filmes.
        
        :param individual: Lista de IDs de filmes representando o indivíduo.
        :return: Uma tupla contendo o valor de adequação (fitness).
        """
        
        # Certifica-se de que o indivíduo não tem IDs repetidos e pertence ao conjunto de todos os IDs.
        if len(individual) != len(set(individual)):
            return (0.0, )
        if len(list(set(individual) - set(self.all_ids))) > 0:
            return (0.0, )

        # Definição de pesos para critérios de avaliação
        YEAR_INTERVAL = 5
        PESO_GENERO = 3
        PESO_NOTA = 2
        PESO_ANO = 1

        # Consulta filmes do banco de dados com base nos IDs fornecidos
        movies_from_db = {movie_id: MovieRepository.find_by_id(self.db, movie_id) for movie_id in individual}

        # Determina os filmes do indivíduo que o usuário ainda não assistiu
        filmes_nao_assistidos = list(set(individual) - set(self.lista_filmes_usuario_asistiu))

        # Calcula médias dos ratings dos filmes não assistidos
        media_filmes = {}
        ratings_dos_filmes = RatingsRepository.find_by_movieid_list(self.db, filmes_nao_assistidos)
        for filme_id in filmes_nao_assistidos:
            ratings_do_filme = [rating for rating in ratings_dos_filmes if rating.movieId == filme_id]
            if ratings_do_filme:
                media_do_filme = sum([rating.rating for rating in ratings_do_filme]) / len(ratings_do_filme)
                media_filmes[filme_id] = media_do_filme

        # Filmes cuja média de avaliação é superior à média do usuário
        filmes_acima_da_media_usuario = [filme_id for filme_id, media in media_filmes.items() if media > self.media_nota_filmes_usuario_asistiu]

        # Filmes que correspondem ao intervalo de anos preferido
        filmes_intervalo_anos = [
            filme_id for filme_id in filmes_nao_assistidos 
            if movies_from_db[filme_id].year is not None and 
            self.media_ano_filmes_usuario_asistiu - YEAR_INTERVAL <= movies_from_db[filme_id].year <= self.media_ano_filmes_usuario_asistiu + YEAR_INTERVAL
        ]

        # Filmes que se encaixam nos gêneros preferidos do usuário
        filmes_genero_preferido = [filme for filme in filmes_nao_assistidos if any(genero in self.lista_generos_usuario for genero in movies_from_db[filme].genres.split('|'))]

        # Cálculo final da adequação (fitness)
        fitness = len(filmes_acima_da_media_usuario) * PESO_NOTA + len(filmes_intervalo_anos) * PESO_ANO + len(filmes_genero_preferido) * PESO_GENERO

        print(fitness)
        
        return (fitness,  )
        

