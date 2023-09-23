from typing import List, Union
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session 

from db.models import Movie
from db.database import engine, Base, get_db
from db.repositories import MovieRepository, UserRepository, RatingsRepository
from db.schemas import MovieRequest, MovieResponse, UserRequest, UserResponse, RatingsResponse, RatingsRequest

from ga.schemas import GeneticConfiguration

from ga.mygenetic import MyGeneticAlgorithm

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Genetic Algorithm Movie Recommender API",
    description="An API to recommeder movies using genetic algorithm approach",
    version="0.0.1",
    terms_of_service=None,
    contact=None,
    license_info=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.get("/api/movies", response_model=List[MovieResponse],
         name="Get all movies",
         description="Return all movies from database.")
def find_all_movies(db: Session = Depends(get_db)):
    movies = MovieRepository.find_all(db)
    return [MovieResponse.from_orm(movie) for movie in movies]


@app.get("/api/movies/{id}", response_model=MovieResponse,
         name="Get movie by id",
         description="Return a especific movie by id.")
def find_movie_by_id(id: int, db: Session = Depends(get_db)):
    movie = MovieRepository.find_by_id(db, id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found."
        )
    
    return MovieResponse.from_orm(movie)

@app.get("/api/users", response_model=List[UserResponse],
         name="Get all users",
         description="Return all users from database.")
def find_all_users(db: Session = Depends(get_db)):
    users = UserRepository.find_all(db)

    return [UserResponse.from_orm(user) for user in users]

@app.get("/api/users/{id}", response_model=UserResponse,
         name="Get user by id",
         description="Return a especific user by id.")
def find_user_by_id(id: int, db: Session = Depends(get_db)):
    user = UserRepository.find_by_id(db, id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    
    return UserResponse.from_orm(user)


@app.get("/api/movies_by_user/{user_id}", response_model=List[RatingsResponse],
         name="Get all movies rated by user",
         description="Return all movies that was rated by a user with the rating.")
def find_movies_by_user(user_id: int, db: Session = Depends(get_db)):

    ratings = RatingsRepository.find_by_userid(db, user_id)
    
    if len(ratings) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    
    return [RatingsResponse.from_orm(rating) for rating in ratings]


@app.get("/api/users_by_movie/{movie_id}", response_model=List[RatingsResponse],
         name="Get all users that rated a movie",
         description="Return all users that rated a movie with the rating.")
def find_users_by_movie(movie_id: int, db: Session = Depends(get_db)):

    ratings = RatingsRepository.find_by_movieid(db, movie_id)
    
    if len(ratings) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found."
        )
    
    return [RatingsResponse.from_orm(rating) for rating in ratings]


@app.post("/api/recommender",
          name="Generate recommender to user",
          description="Train a genetic algorithm to generate a recommender to user")
def recommender(configuration: GeneticConfiguration, db: Session = Depends(get_db)):
    movies = MovieRepository.find_all(db)
    all_ids = [movie.movieId for movie in movies]

    p_crossover = configuration.p_crossover / 100
    p_mutatioin = configuration.p_mutation / 100
    
    my_genetic = MyGeneticAlgorithm(
        configuration.query_search,
        configuration.individual_size, 
        configuration.population_size, 
        p_crossover,
        p_mutatioin,
        all_ids, 
        configuration.max_generations, 
        configuration.size_hall_of_fame, 
        (1.0, ),
        configuration.seed,
        db
        )
    
    my_genetic.eval()
    log = my_genetic.get_log()
    best = my_genetic.get_best()

    recommender_movies = MovieRepository.find_all_ids(db, best)

    return {'logs': log, 'best': recommender_movies}




if __name__ == '__main__':
    uvicorn.run('main:app', host='localhost', port=8000)