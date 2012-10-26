/*
eggfill.c

Fill function and queue list


Copyright 2007, NATE-LSI-EPUSP

Oficina is developed in Brazil at Escola Politécnica of 
Universidade de São Paulo. NATE is part of LSI (Integrable
Systems Laboratory) and stands for Learning, Work and Entertainment
Research Group. Visit our web page: 
www.lsi.usp.br/nate
Suggestions, bugs and doubts, please email oficina@lsi.usp.br

Oficina is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License 
as published by the Free Software Foundation version 2 of 
the License.

Oficina is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with Oficina; if not, write to the
Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, 
Boston, MA  02110-1301  USA.
The copy of the GNU General Public License is found in the 
COPYING file included in the source distribution.


Authors:

Joyce Alessandra Saul               (joycealess@gmail.com)
Andre Mossinato                     (andremossinato@gmail.com)
Nathalia Sautchuk Patrício          (nathalia.sautchuk@gmail.com)
Pedro Kayatt                        (pekayatt@gmail.com)
Rafael Barbolo Lopes                (barbolo@gmail.com)
Alexandre A. Gonçalves Martinazzo   (alexandremartinazzo@gmail.com)

Colaborators:
Bruno Gola                          (brunogola@gmail.com)

Group Manager:
Irene Karaguilla Ficheman           (irene@lsi.usp.br)

Cientific Coordinator:
Roseli de Deus Lopes                (roseli@lsi.usp.br)

*/

#include "eggfill.h"

#define front(q)   ( (q)->front )
#define rear(q)    ( (q)->rear )

/* this queue has a Header that points to the Front and Rear elements */
/* empty queue: q->front = NULL and q->rear = NULL                      */

/* check if queue q is empty */
int queue_is_empty(queue *q){
	return ((front(q)==NULL) && (rear(q)==NULL));
}

queue *queue_init(void){
    queue *q;
    q = (queue*)malloc(sizeof(queue));
    /* check if there is enough space */
    if( q == NULL )
        printf( "Out of space!!!" );
    q->front = NULL;
    q->rear = NULL;
    
    return q;
}

void queue_destroy(queue *q){
	queue_make_empty(q);
	free(q);
}

void queue_make_empty(queue *q){
    if( q == NULL )
    	printf( "Must use CreateQueue first" );
    else
        while( !queue_is_empty(q) )
            queue_dequeue(q);
}

void queue_enqueue(int element, queue *q){
    no *tmp;
    tmp = (no*)malloc(sizeof(no));
    if(tmp == NULL) {
        printf("Out of space!!!");
        return;
    } else {
        tmp->info = element;
	tmp->next = NULL;
	if (queue_is_empty(q)){
	    q->front = tmp;
	} else { 
	    q->rear->next = tmp;
	}
	q->rear = tmp;
    }
}

void queue_dequeue(queue *q){
    if(queue_is_empty(q)) {
        printf( "Empty queue" );
    }
    else {
        no *tmp = q->front;
        q->front = q->front->next;
        if (q->front==NULL) {
		    q->rear=NULL;
        }
        free(tmp);
    }
}/* end of queue*/

void
floodfill(unsigned int* pixels, int x, int y, int width, int height, unsigned int color) {

    printf("\nEntrando to floodfill\n");
    queue *lista_xy;
    
    lista_xy = queue_init();

    int color_start = pixels[x + y * width];
   
    if (color != color_start) {
        queue_enqueue(x, lista_xy);
        queue_enqueue(y, lista_xy);

        pixels[x + y * width] = color;

        while (!queue_is_empty(lista_xy)) {
            if (x + 1 < width) {
                if (pixels[(x + 1) + y * width] == color_start) {
                    pixels[(x + 1) + y * width] = color;
                    queue_enqueue(x+1, lista_xy);
                    queue_enqueue(y, lista_xy);
                }
            }

            if (x - 1 >= 0){
                if (pixels[(x - 1) + y * width] == color_start) {
                    pixels[(x - 1) + y * width] = color;
                    queue_enqueue(x-1, lista_xy);
                    queue_enqueue(y, lista_xy);
                }
            }

            if (y + 1 < height){
                if (pixels[x + (y + 1) * width] == color_start) {
                    pixels[x + (y + 1) * width] = color;
                    queue_enqueue(x, lista_xy);
                    queue_enqueue(y+1, lista_xy);
                }
            }

            if (y - 1 >= 0){
                if (pixels[x + (y - 1) * width] == color_start){
                    pixels[x + (y - 1) * width] = color;
                    queue_enqueue(x, lista_xy);
                    queue_enqueue(y-1, lista_xy);
                }
            }
            x = lista_xy->front->info;
            queue_dequeue(lista_xy);
            y = lista_xy->front->info;
            queue_dequeue(lista_xy);
       }
   }
   queue_destroy(lista_xy);
} 

